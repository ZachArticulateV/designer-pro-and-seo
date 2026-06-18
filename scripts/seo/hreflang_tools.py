#!/usr/bin/env python3
"""
hreflang_tools.py — hreflang validator + generator for international SEO.

Validates a set of hreflang annotations for the common, ranking-costing mistakes
(invalid language/region codes, missing self-reference, missing x-default, dupes)
and generates correct <link rel="alternate" hreflang="..."> tags from a
locale->URL map.

Note: full return-link reciprocity requires fetching every alternate page; this
tool validates the structure of one set and flags what to verify across pages.

Standard library only. Deterministic.

Usage:
  # generate from a JSON map {"en-us":"https://site.com/","fr-fr":"https://site.com/fr/"}
  python3 hreflang_tools.py --generate --map locales.json [--x-default https://site.com/]
  # validate a JSON list [{"hreflang":"en-us","href":"https://..."}, ...] (file or inline)
  python3 hreflang_tools.py --validate cluster.json --self https://site.com/
"""
import argparse
import json
import os
import re
import sys

# Minimal ISO 639-1 language subset (common) + special "x-default".
ISO639 = {"aa","ab","af","am","ar","as","az","be","bg","bn","bs","ca","cs","cy","da",
          "de","el","en","es","et","eu","fa","fi","fr","ga","gl","gu","he","hi","hr",
          "hu","hy","id","is","it","ja","ka","kk","km","kn","ko","lt","lv","mk","ml",
          "mr","ms","mt","nb","ne","nl","no","pa","pl","ps","pt","ro","ru","sk","sl",
          "sq","sr","sv","sw","ta","te","th","tl","tr","uk","ur","vi","zh"}
# Region codes are ISO 3166-1 alpha-2; validate shape, not full list.
REGION_RE = re.compile(r"^[A-Z]{2}$")


def validate_code(code):
    if code == "x-default":
        return True, ""
    parts = code.split("-")
    lang = parts[0].lower()
    if lang not in ISO639:
        return False, f"language '{parts[0]}' not a valid ISO 639-1 code"
    if len(parts) == 2:
        if not REGION_RE.match(parts[1].upper()):
            return False, f"region '{parts[1]}' must be ISO 3166-1 alpha-2 (e.g. US, GB)"
    elif len(parts) > 2:
        return False, f"'{code}' has too many segments (use lang or lang-REGION)"
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
    ap.add_argument("--self", dest="self_url", default=None, help="this page's URL (for self-ref check)")
    args = ap.parse_args()

    try:
        if args.validate:
            out = validate(_load(args.validate), args.self_url)
        elif args.generate:
            if not args.map:
                print(json.dumps({"error": "--generate needs --map (JSON file or inline)"}))
                sys.exit(1)
            out = generate(_load(args.map), args.x_default)
        else:
            print("Use --generate (with --map) or --validate.", file=sys.stderr)
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
