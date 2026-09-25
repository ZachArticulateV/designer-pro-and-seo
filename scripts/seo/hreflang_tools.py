#!/usr/bin/env python3
"""
hreflang_tools.py — hreflang validator + generator for international SEO.

Validates a set of hreflang annotations for the common, ranking-costing mistakes
(invalid language/region codes, missing self-reference, missing x-default, dupes)
and generates correct <link rel="alternate" hreflang="..."> tags from a
locale->URL map.

--cluster checks the whole set across pages: pass the alternate pages' HTML (a manifest
{url: file}, or files whose canonical gives their URL) and it verifies self-references,
return links, code agreement, x-default consistency, <html lang> agreement, and that no
alternate is noindex or canonicalized elsewhere.

Standard library only. Deterministic.

Usage:
  # generate from a JSON map {"en-us":"https://site.com/","fr-fr":"https://site.com/fr/"}
  python3 hreflang_tools.py --generate --map locales.json [--x-default https://site.com/]
  # validate a JSON list [{"hreflang":"en-us","href":"https://..."}, ...] (file or inline)
  python3 hreflang_tools.py --validate cluster.json --self https://site.com/
  # cross-page cluster audit
  python3 hreflang_tools.py --cluster manifest.json        # {"https://site.com/": "en.html", ...}
  python3 hreflang_tools.py --cluster en.html fr.html de.html
"""
import argparse
import json
import os
import re
import sys

# ISO 639-1 language codes (hreflang accepts only these two-letter codes) + x-default.
ISO639 = set("""aa ab ae af ak am an ar as av ay az ba be bg bi bm bn bo br bs ca ce ch co
cr cs cu cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha
he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr
ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl
nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm
sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo
wa wo xh yi yo za zh zu""".split())
# Region codes are ISO 3166-1 alpha-2; validate shape + the classic mistakes.
REGION_RE = re.compile(r"^[A-Z]{2}$")
SCRIPT_RE = re.compile(r"^[A-Z][a-z]{3}$")          # ISO 15924, e.g. Hans, Hant, Latn
LANG_HINT = {"jp": "ja", "cn": "zh", "dk": "da", "gr": "el", "cz": "cs", "ua": "uk",
             "vn": "vi", "kz": "kk", "iw": "he", "in": "id", "ji": "yi"}
REGION_HINT = {"UK": "GB", "EN": None, "EU": None, "LA": None}


def validate_code(code):
    if code.lower() == "x-default":
        return True, ""
    parts = code.split("-")
    lang = parts[0].lower()
    if lang not in ISO639:
        hint = LANG_HINT.get(lang)
        return False, (f"language '{parts[0]}' not a valid ISO 639-1 code"
                       + (f" (did you mean '{hint}'?)" if hint else ""))
    rest = parts[1:]
    if rest and SCRIPT_RE.match(rest[0].capitalize()) and len(rest[0]) == 4:
        rest = rest[1:]                       # lang-Script[-REGION], e.g. zh-Hant-TW
    if len(rest) == 1:
        region = rest[0].upper()
        if region.isdigit():
            return False, f"numeric region '{rest[0]}' (UN M.49) is not supported; use ISO 3166-1 alpha-2"
        if not REGION_RE.match(region):
            return False, f"region '{rest[0]}' must be ISO 3166-1 alpha-2 (e.g. US, GB)"
        if region in REGION_HINT:
            fix = REGION_HINT[region]
            return False, (f"region '{rest[0]}' is not a country code"
                           + (f" (use '{fix}')" if fix else " (target countries individually or use the language alone)"))
    elif len(rest) > 1:
        return False, f"'{code}' has too many segments (use lang, lang-REGION or lang-Script-REGION)"
    return True, ""


def validate(entries, self_url=None):
    if not isinstance(entries, list):
        return {"action": "validate", "count": 0, "valid": False,
                "errors": ["expected a JSON list of {hreflang, href} objects"],
                "warnings": []}
    errors, warnings = [], []
    seen = {}
    has_xdefault = False
    has_self = False
    for e in entries:
        code = e.get("hreflang", "")
        href = e.get("href", "")
        ok, msg = validate_code(code)
        if not ok:
            errors.append(f"{code}: {msg}")
        if code == "x-default":
            has_xdefault = True
        if href and not re.match(r"^https?://", href):
            errors.append(f"{code}: href is not absolute ({href})")
        key = code.lower()
        if key in seen:
            errors.append(f"duplicate hreflang '{code}'")
        seen[key] = href
        if self_url and href == self_url:
            has_self = True
    if self_url and not has_self:
        errors.append("no self-referencing hreflang (each page must list itself)")
    if not has_xdefault:
        warnings.append("no x-default (recommended for unmatched languages/regions)")
    warnings.append("verify return links: every alternate must point back (reciprocity) — needs per-page fetch")
    return {"action": "validate", "count": len(entries), "valid": not errors,
            "errors": errors, "warnings": warnings}


def generate(locale_map, x_default=None):
    if not isinstance(locale_map, dict):
        return {"action": "generate", "tags": [],
                "errors": ["expected a JSON object {locale: url}"], "note": ""}
    tags, errors = [], []
    for code, href in locale_map.items():
        ok, msg = validate_code(code)
        if not ok:
            errors.append(f"{code}: {msg}")
        tags.append(f'<link rel="alternate" hreflang="{code}" href="{href}" />')
    if x_default:
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{x_default}" />')
    return {"action": "generate", "tags": tags, "errors": errors,
            "note": "Place these in <head> on EVERY alternate page (including a self-reference), or return them via the Link: HTTP header / XML sitemap."}


# --- cross-page cluster audit -------------------------------------------------------

def _attrs(tag):
    return {k.lower(): v for k, v in re.findall(r'([\w:-]+)\s*=\s*["\']([^"\']*)["\']', tag)}


def extract_page(html):
    """hreflang map, canonical, <html lang> and noindex from one HTML document."""
    alts, canonical, noindex = {}, None, False
    for tag in re.findall(r"<link\b[^>]*>", html, re.I):
        a = _attrs(tag)
        rel = a.get("rel", "").lower().split()
        if "alternate" in rel and a.get("hreflang"):
            alts.setdefault(a["hreflang"].strip(), a.get("href", "").strip())
        elif "canonical" in rel and canonical is None:
            canonical = a.get("href", "").strip() or None
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        a = _attrs(tag)
        if a.get("name", "").lower() in ("robots", "googlebot") and "noindex" in a.get("content", "").lower():
            noindex = True
    m = re.search(r"<html\b[^>]*\blang\s*=\s*[\"']([^\"']+)", html, re.I)
    return {"alternates": alts, "canonical": canonical,
            "lang": m.group(1) if m else None, "noindex": noindex}


def _n(u):
    return (u or "").strip().rstrip("/")


def cluster(pages):
    """pages: {url: extract_page(...)}. Returns the cross-page hreflang report."""
    issues = []

    def add(sev, code, finding, where, fix):
        issues.append({"severity": sev, "code": code, "finding": finding,
                       "pages": sorted(set(where))[:10], "fix": fix})

    urls = {_n(u): u for u in pages}
    xdefaults = set()
    for url, info in pages.items():
        alts = info["alternates"]
        if not alts:
            add("high", "H1", "page has no hreflang annotations", [url],
                "Every page in the cluster needs the full set, including itself.")
            continue
        for code in alts:
            ok, msg = validate_code(code)
            if not ok:
                add("high", "H2", f"invalid code {code}: {msg}", [url], "Use ISO 639-1[-ISO 3166-1].")
        if _n(url) not in {_n(h) for c, h in alts.items() if c.lower() != "x-default"}:
            add("high", "H3", "missing self-referencing hreflang", [url],
                "List the page itself with its own code.")
        if "x-default" in {c.lower() for c in alts}:
            xdefaults.add(_n(alts.get("x-default") or alts.get("X-default") or ""))
        else:
            add("medium", "H4", "no x-default", [url],
                "Add an x-default for users matching no listed locale.")
        rel = [h for h in alts.values() if not re.match(r"^https?://", h)]
        if rel:
            add("high", "H5", f"{len(rel)} non-absolute hreflang href(s)", [url], "Use absolute URLs.")
        for code, href in alts.items():
            target = urls.get(_n(href))
            if code.lower() == "x-default" or _n(href) == _n(url):
                continue
            if target is None:
                add("info", "H6", f"alternate {href} not in the audited set", [url],
                    "Include it to verify return links.")
                continue
            back = {c: h for c, h in pages[target]["alternates"].items()
                    if c.lower() != "x-default"}      # x-default is not a return link
            if _n(url) not in {_n(h) for h in back.values()}:
                add("high", "H7", f"no return link: {target} does not point back", [url, target],
                    "Alternates must reference each other (A->B needs B->A); otherwise "
                    "the pair is ignored.")
            else:
                my_code_there = [c for c, h in back.items() if _n(h) == _n(url)]
                my_code_here = [c for c, h in alts.items()
                                if _n(h) == _n(url) and c.lower() != "x-default"]
                if my_code_here and my_code_there and my_code_here[0].lower() != my_code_there[0].lower():
                    add("medium", "H8", f"{url} is {my_code_here[0]} on itself but "
                                        f"{my_code_there[0]} on {target}", [url, target],
                        "Use one code per URL across the whole cluster.")
        # the page's own annotation vs its <html lang>
        own = [c for c, h in alts.items() if _n(h) == _n(url) and c.lower() != "x-default"]
        if own and info.get("lang") and own[0].split("-")[0].lower() != info["lang"].split("-")[0].lower():
            add("medium", "H9", f"hreflang {own[0]} disagrees with <html lang=\"{info['lang']}\">",
                [url], "Make the page language, lang attribute and hreflang agree.")
        if info.get("noindex"):
            add("high", "H10", "alternate page is noindex", [url],
                "hreflang alternates must be indexable; drop the noindex or the annotation.")
        if info.get("canonical") and _n(info["canonical"]) != _n(url):
            add("high", "H11", f"alternate canonicalizes to {info['canonical']}", [url],
                "Each language version must be self-canonical; never canonicalize across locales.")
    if len(xdefaults) > 1:
        add("medium", "H12", f"{len(xdefaults)} different x-default targets", list(pages),
            "Point every page's x-default at the same URL.")

    # dedupe identical findings (a missing return link is reported from both sides)
    seen, unique = set(), []
    for i in issues:
        key = (i["code"], i["finding"])
        if key not in seen:
            seen.add(key)
            unique.append(i)
    penalty = {"critical": 25, "high": 10, "medium": 4, "info": 0}
    codes = {}
    for i in unique:
        codes.setdefault(i["code"], i["severity"])
    return {"action": "cluster", "pages": len(pages), "issues": unique,
            "score": max(0, 100 - sum(penalty[s] for s in codes.values())),
            "ok": not any(i["severity"] in ("critical", "high") for i in unique)}


def _load_cluster(args):
    pages = {}
    if len(args) == 1 and args[0].lower().endswith(".json"):
        manifest = _load(args[0])
        base = os.path.dirname(os.path.abspath(args[0]))
        for url, path in manifest.items():
            full = path if os.path.isabs(path) else os.path.join(base, path)
            with open(full, encoding="utf-8", errors="replace") as fh:
                pages[url] = extract_page(fh.read())
        return pages
    for path in args:
        with open(path, encoding="utf-8", errors="replace") as fh:
            info = extract_page(fh.read())
        if not info["canonical"]:
            raise ValueError(f"{path} has no canonical; use a {{url: file}} manifest instead")
        pages[info["canonical"]] = info
    return pages


def _load(arg):
    if os.path.exists(arg):
        with open(arg, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--map", help="JSON {locale: url} for --generate")
    ap.add_argument("--x-default", default=None)
    ap.add_argument("--validate", help="JSON list of {hreflang, href} (file or inline)")
    ap.add_argument("--cluster", nargs="+", help="manifest.json {url: file} or HTML files (URL from canonical)")
    ap.add_argument("--self", dest="self_url", default=None, help="this page's URL (for self-ref check)")
    args = ap.parse_args()

    try:
        if args.cluster:
            try:
                out = cluster(_load_cluster(args.cluster))
            except ValueError as e:
                print(json.dumps({"error": str(e)}))
                sys.exit(1)
        elif args.validate:
            out = validate(_load(args.validate), args.self_url)
        elif args.generate:
            if not args.map:
                print(json.dumps({"error": "--generate needs --map (JSON file or inline)"}))
                sys.exit(1)
            out = generate(_load(args.map), args.x_default)
        else:
            print("Use --generate (with --map), --validate, or --cluster.", file=sys.stderr)
            sys.exit(2)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": "could not read JSON input: %s" % e}))
        sys.exit(1)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
