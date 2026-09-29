#!/usr/bin/env python3
"""
sitemap_tools.py — XML sitemap generator, validator and quality-gate cross-checker.

Modes:
  --generate --urls urls.txt --out sitemap.xml [--lastmod D | --lastmod-file map.csv]
        sitemaps.org-compliant urlset (or an index + children past 50,000 URLs)
  --validate FILE|XML [--as-of YYYY-MM-DD]
        structure + honesty checks: well-formedness (gzip too), root type, 50,000 URL /
        50 MB limits, absolute + same-host locs, duplicates, fragments, session ids,
        lastmod format / future / all-identical (auto-bumped), ignored changefreq /
        priority, and the image / video / news / hreflang (xhtml:link) extensions
  --crosscheck FILE --pages pages.json
        the quality gates: sitemap URLs that are non-200, redirected, noindex, or
        canonicalized elsewhere, plus known indexable pages missing from the sitemap.
        pages.json = [{"url", "status", "noindex"?, "canonical"?, "final_url"?}]
  --check-live FILE [--sample N]
        builds pages.json for the first N sitemap URLs by fetching them through the
        shared SSRF guard (status, redirect, meta robots / X-Robots-Tag, canonical),
        then cross-checks; states its sampling boundary

Every finding is {severity, code, finding, fix}; a deterministic 0-100 score
(100 − 25/critical − 10/high − 4/medium) accompanies each report. Backward-compatible
keys (action/root/valid/errors/warnings/url_count) are kept.

Standard library only. Offline except --check-live.
"""
import argparse
import datetime as _dt
import gzip
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import safe_open, UrlValidationError, SafeFetchError  # noqa: E402

MAX_URLS = 50000
MAX_BYTES = 50 * 1024 * 1024
MAX_NEWS = 1000
SM_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
NS = {
    "sm": SM_NS,
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
    "video": "http://www.google.com/schemas/sitemap-video/1.1",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}
W3C_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2}))?)?)?$")
PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}
UA = "Mozilla/5.0 (compatible; designer-pro-seo-sitemap/1.1)"


def _q(prefix, tag):
    return "{%s}%s" % (NS[prefix], tag)


def _read_urls(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def _esc(u):
    return (u.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))


# --- generate ---------------------------------------------------------------------------

def build_urlset(urls, lastmod=None, lastmods=None):
    lastmods = lastmods or {}
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<urlset xmlns="{SM_NS}">']
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{_esc(u)}</loc>")
        lm = lastmods.get(u, lastmod)
        if lm:
            lines.append(f"    <lastmod>{lm}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build_index(sitemap_urls, lastmod=None):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<sitemapindex xmlns="{SM_NS}">']
    for u in sitemap_urls:
        lines.append("  <sitemap>")
        lines.append(f"    <loc>{_esc(u)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </sitemap>")
    lines.append("</sitemapindex>")
    return "\n".join(lines) + "\n"


def generate(urls, out, lastmod=None, base_url="", lastmods=None):
    warnings = []
    bad = [u for u in urls if urlparse(u).scheme not in ("http", "https")]
    if bad:
        warnings.append(f"{len(bad)} URL(s) are not absolute http(s) — first: {bad[0]}")
    seen, clean = set(), []
    for u in urls:
        if urlparse(u).scheme in ("http", "https") and u not in seen:
            seen.add(u)
            clean.append(u)
    if len(clean) < len(urls) - len(bad):
        warnings.append(f"{len(urls) - len(bad) - len(clean)} duplicate URL(s) dropped")
    urls = clean
    if lastmod and not lastmods:
        warnings.append("one --lastmod stamped on every URL: use --lastmod-file with real "
                        "per-URL change dates, or Google learns to ignore lastmod")

    written = []
    if len(urls) <= MAX_URLS:
        xml = build_urlset(urls, lastmod, lastmods)
        with open(out, "w", encoding="utf-8") as f:
            f.write(xml)
        written.append(out)
        size = os.path.getsize(out)
        if size > MAX_BYTES:
            warnings.append(f"{out} is {size//1024//1024}MB (> 50MB limit) — split it.")
    else:
        stem, ext = os.path.splitext(out)
        chunks = [urls[i:i + MAX_URLS] for i in range(0, len(urls), MAX_URLS)]
        child_urls = []
        for idx, chunk in enumerate(chunks, 1):
            cpath = f"{stem}-{idx}{ext}"
            with open(cpath, "w", encoding="utf-8") as f:
                f.write(build_urlset(chunk, lastmod, lastmods))
            written.append(cpath)
            loc = (base_url.rstrip("/") + "/" + os.path.basename(cpath)) if base_url else os.path.basename(cpath)
            child_urls.append(loc)
        with open(out, "w", encoding="utf-8") as f:
            f.write(build_index(child_urls, lastmod))
        written.insert(0, out)
        if not base_url:
            warnings.append("split into an index but no --base-url given; child <loc> are filenames, not absolute URLs — fix before deploy.")
    return {"action": "generate", "url_count": len(urls), "files": written, "warnings": warnings}


# --- validate ---------------------------------------------------------------------------

def _load_raw(path_or_xml):
    """(raw_text, size_bytes, error). Accepts a path (gzip-aware) or raw XML."""
    if os.path.exists(path_or_xml):
        try:
            with open(path_or_xml, "rb") as f:
                data = f.read()
        except OSError as e:
            return None, 0, f"could not read: {e}"
        if data[:2] == b"\x1f\x8b":
            try:
                data = gzip.decompress(data)
            except OSError as e:
                return None, 0, f"bad gzip: {e}"
        return data.decode("utf-8", "replace"), len(data), None
    return path_or_xml, len(path_or_xml.encode("utf-8")), None


def _parse_date(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if not m:
        return None
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def validate(path_or_xml, as_of=None):
    issues = []

    def add(sev, code, finding, fix=""):
        issues.append({"severity": sev, "code": code, "finding": finding, "fix": fix})

    raw, size, err = _load_raw(path_or_xml)
    if err:
        return {"action": "validate", "valid": False, "errors": [err], "warnings": [],
                "issues": [], "score": 0}
    if size > MAX_BYTES:
        add("critical", "S02", f"{size//1024//1024}MB uncompressed (> 50MB protocol limit)",
            "Split into several sitemaps under a sitemap index.")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return {"action": "validate", "valid": False,
                "errors": [f"not well-formed XML: {e}"], "warnings": [],
                "issues": [{"severity": "critical", "code": "S01",
                            "finding": f"not well-formed XML: {e}",
                            "fix": "Escape & < > in URLs and close every tag."}], "score": 0}

    tag = root.tag.split("}")[-1]
    ns = "{" + SM_NS + "}"
    result = {"action": "validate", "root": tag}
    if root.tag.split("}")[0].strip("{") != SM_NS:
        add("high", "S03", "namespace is not the sitemaps.org 0.9 schema",
            f'Use xmlns="{SM_NS}".')

    if tag == "urlset":
        entries = root.findall(ns + "url")
        locs = [(e.findtext(ns + "loc") or "").strip() for e in entries]
        result["url_count"] = len(locs)
        if not locs:
            add("critical", "S04", "urlset contains no <url> entries", "List the indexable URLs.")
        if len(locs) > MAX_URLS:
            add("critical", "S05", f"{len(locs)} URLs (> 50,000 limit)", "Use a sitemap index.")
        non_abs = [u for u in locs if urlparse(u).scheme not in ("http", "https")]
        if non_abs:
            add("critical", "S06", f"{len(non_abs)} <loc> are not absolute http(s) (e.g. {non_abs[0]!r})",
                "Use full https:// URLs.")
        absu = [u for u in locs if u not in non_abs]
        hosts = sorted({urlparse(u).netloc.lower() for u in absu})
        schemes = sorted({urlparse(u).scheme for u in absu})
        if len(hosts) > 1:
            add("high", "S07", f"URLs span {len(hosts)} hosts: {', '.join(hosts[:3])}",
                "A sitemap may only list URLs on its own host (pick www or non-www).")
        if len(schemes) > 1:
            add("high", "S08", "mix of http:// and https:// URLs",
                "List only the canonical https:// URLs.")
        dups = len(locs) - len(set(locs))
        if dups:
            add("medium", "S09", f"{dups} duplicate <loc>", "List each URL once.")
        frag = [u for u in absu if "#" in u]
        if frag:
            add("medium", "S10", f"{len(frag)} URL(s) with #fragments", "Drop fragments; they are not separate pages.")
        sess = [u for u in absu if re.search(r"[?&](sid|sessionid|phpsessid|jsessionid|utm_\w+)=", u, re.I)]
        if sess:
            add("medium", "S11", f"{len(sess)} URL(s) with session/tracking parameters",
                "List clean canonical URLs only.")

        # lastmod honesty
        lms = [(e.findtext(ns + "lastmod") or "").strip() for e in entries]
        present = [l for l in lms if l]
        bad_fmt = [l for l in present if not W3C_DATE.match(l)]
        if bad_fmt:
            add("medium", "S12", f"{len(bad_fmt)} lastmod not in W3C datetime format (e.g. {bad_fmt[0]!r})",
                "Use YYYY-MM-DD or a full timestamp with timezone.")
        if as_of:
            future = [l for l in present if (_parse_date(l) or _dt.date.min) > as_of]
            if future:
                add("medium", "S13", f"{len(future)} lastmod date(s) in the future",
                    "lastmod must be the real last content change.")
        if len(present) >= 10:
            top = max(present.count(v) for v in set(present))
            if top / len(present) > 0.9:
                add("medium", "S14", f"{top}/{len(present)} URLs share one lastmod (auto-bumped?)",
                    "Stamp lastmod from real per-page change dates; Google ignores lastmod it can't trust.")
        if locs and not present:
            add("info", "S15", "no lastmod values", "Add real lastmod dates so changed pages get recrawled sooner.")
        if root.findall(".//" + ns + "changefreq") or root.findall(".//" + ns + "priority"):
            add("info", "S16", "changefreq / priority present (Google ignores both)",
                "Optional to keep; spend the effort on accurate lastmod.")

        _validate_extensions(root, entries, ns, add, as_of)
    elif tag == "sitemapindex":
        sms = [(e.text or "").strip() for e in root.iter(ns + "loc")]
        result["sitemap_count"] = len(sms)
        if not sms:
            add("critical", "S04", "sitemapindex contains no <sitemap> entries", "List child sitemaps.")
        if len(sms) > MAX_URLS:
            add("critical", "S05", f"{len(sms)} child sitemaps (> 50,000 limit)", "Split the index.")
        rel = [u for u in sms if urlparse(u).scheme not in ("http", "https")]
        if rel:
            add("critical", "S06", f"{len(rel)} child <loc> are not absolute http(s)",
                "Use full https:// URLs for every child sitemap.")
    else:
        add("critical", "S04", f"unexpected root <{tag}> (expected urlset or sitemapindex)", "")

    errors = [i["finding"] for i in issues if i["severity"] in ("critical", "high")
              and i["code"] in ("S01", "S02", "S04", "S05", "S06")]
    result.update({
        "valid": not errors, "errors": errors,
        "warnings": [i["finding"] for i in issues if i["finding"] not in errors
                     and i["severity"] != "info"],
        "issues": issues,
        "score": max(0, 100 - sum(PENALTY[i["severity"]] for i in issues)),
    })
    return result


def _validate_extensions(root, entries, ns, add, as_of):
    imgs = root.findall(".//" + _q("image", "image"))
    if imgs:
        bad = [i for i in imgs if urlparse((i.findtext(_q("image", "loc")) or "").strip()).scheme
               not in ("http", "https")]
        if bad:
            add("high", "S20", f"{len(bad)}/{len(imgs)} image:loc missing or not absolute",
                "Every image:image needs an absolute image:loc.")
    vids = root.findall(".//" + _q("video", "video"))
    for v in vids:
        need = [t for t in ("thumbnail_loc", "title", "description") if not v.findtext(_q("video", t))]
        if not (v.findtext(_q("video", "content_loc")) or v.findtext(_q("video", "player_loc"))):
            need.append("content_loc|player_loc")
        if need:
            add("high", "S21", "video entry missing " + ", ".join(need),
                "video:video needs thumbnail_loc, title, description and content_loc or player_loc.")
            break
    news = root.findall(".//" + _q("news", "news"))
    if news:
        if len(news) > MAX_NEWS:
            add("high", "S22", f"{len(news)} news entries (> 1,000 per news sitemap)",
                "Split news sitemaps; keep only recent articles.")
        for n in news:
            pub = n.find(_q("news", "publication"))
            miss = []
            if pub is None or not pub.findtext(_q("news", "name")) or not pub.findtext(_q("news", "language")):
                miss.append("publication name/language")
            if not n.findtext(_q("news", "publication_date")):
                miss.append("publication_date")
            if not n.findtext(_q("news", "title")):
                miss.append("title")
            if miss:
                add("high", "S23", "news entry missing " + ", ".join(miss), "Complete every news:news block.")
                break
        if as_of:
            old = [n for n in news if (_parse_date(n.findtext(_q("news", "publication_date")) or "")
                                        or as_of) < as_of - _dt.timedelta(days=2)]
            if old:
                add("medium", "S24", f"{len(old)} news entries older than 2 days",
                    "News sitemaps should list only articles from the last 2 days.")
    # hreflang alternates: absolute + reciprocal within this sitemap
    alt_map = {}
    for e in entries:
        loc = (e.findtext(ns + "loc") or "").strip()
        alts = {}
        for l in e.findall(_q("xhtml", "link")):
            if l.get("rel") == "alternate" and l.get("hreflang"):
                alts[l.get("hreflang").lower()] = (l.get("href") or "").strip()
        if alts:
            alt_map[loc] = alts
    if alt_map:
        rel = sum(1 for a in alt_map.values() for h in a.values() if not h.startswith(("http://", "https://")))
        if rel:
            add("high", "S25", f"{rel} xhtml:link hreflang href(s) not absolute", "Use absolute URLs.")
        missing = 0
        for loc, alts in alt_map.items():
            if loc not in alts.values():
                missing += 1          # self-reference absent
            for h in alts.values():
                if h in alt_map and loc not in alt_map[h].values():
                    missing += 1
        if missing:
            add("high", "S26", f"{missing} hreflang self/return link(s) missing",
                "Each URL must list itself and every alternate, and alternates must link back "
                "(validate the cluster with seo-hreflang).")


# --- quality gates ---------------------------------------------------------------------------

def sitemap_locs(path_or_xml):
    raw, _, err = _load_raw(path_or_xml)
    if err:
        raise ValueError(err)
    root = ET.fromstring(raw)
    return [(e.text or "").strip() for e in root.iter("{%s}loc" % SM_NS)]


def crosscheck(locs, pages):
    """Quality gates over supplied page states. pages: list of dicts with url, status,
    noindex?, canonical?, final_url?. Deterministic."""
    by_url = {p["url"]: p for p in pages if isinstance(p, dict) and p.get("url")}
    rows, issues = [], []

    def add(sev, code, finding, urls, fix):
        issues.append({"severity": sev, "code": code, "finding": finding, "urls": urls[:10],
                       "count": len(urls), "fix": fix})

    missing_state, non200, redirected, noindex, canon_else = [], [], [], [], []
    for u in locs:
        p = by_url.get(u)
        if not p:
            missing_state.append(u)
            continue
        st = p.get("status")
        if p.get("final_url") and p["final_url"].rstrip("/") != u.rstrip("/"):
            redirected.append(u)
        elif isinstance(st, int) and st >= 300:
            (redirected if 300 <= st < 400 else non200).append(u)
        if p.get("noindex"):
            noindex.append(u)
        c = (p.get("canonical") or "").strip()
        if c and urljoin(u, c).rstrip("/") != u.rstrip("/"):
            canon_else.append(u)
        rows.append(u)
    if non200:
        add("high", "G1", f"{len(non200)} sitemap URL(s) return 4xx/5xx", non200,
            "Remove dead URLs or restore the pages.")
    if redirected:
        add("medium", "G2", f"{len(redirected)} sitemap URL(s) redirect", redirected,
            "List the final destination URL instead.")
    if noindex:
        add("high", "G3", f"{len(noindex)} sitemap URL(s) are noindex", noindex,
            "Drop noindex pages from the sitemap (mixed signals), or remove the noindex.")
    if canon_else:
        add("high", "G4", f"{len(canon_else)} sitemap URL(s) canonicalize elsewhere", canon_else,
            "List only canonical URLs.")
    locset = set(u.rstrip("/") for u in locs)
    orphans = [p["url"] for p in by_url.values()
               if p.get("status") == 200 and not p.get("noindex")
               and not ((p.get("canonical") or "") and urljoin(p["url"], p["canonical"]).rstrip("/") != p["url"].rstrip("/"))
               and p["url"].rstrip("/") not in locset]
    if orphans:
        add("medium", "G5", f"{len(orphans)} indexable page(s) missing from the sitemap", orphans,
            "Add every canonical, indexable page you want crawled.")
    if missing_state:
        add("info", "G0", f"{len(missing_state)} sitemap URL(s) had no page state supplied",
            missing_state, "Crawl or --check-live them to complete the gates.")
    return {"action": "crosscheck", "sitemap_urls": len(locs), "checked": len(rows),
            "issues": issues,
            "score": max(0, 100 - sum(PENALTY[i["severity"]] for i in issues)),
            "ok": not any(i["severity"] in ("critical", "high") for i in issues)}


def _page_state(url, timeout=10):
    """Fetch one URL (SSRF-guarded) -> {url, status, final_url, noindex, canonical}."""
    try:
        resp, chain = safe_open(url, timeout=timeout, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError) as e:
        return {"url": url, "status": None, "error": str(e)}
    except OSError as e:
        return {"url": url, "status": getattr(e, "code", None), "error": str(e)}
    try:
        status = getattr(resp, "status", None) or getattr(resp, "code", None)
        head = resp.read(300_000).decode("utf-8", "replace")
        xrt = (resp.headers.get("X-Robots-Tag") or "").lower()
    finally:
        resp.close()
    meta = re.search(r'<meta[^>]+name=["\'](?:robots|googlebot)["\'][^>]*content=["\']([^"\']*)', head, re.I)
    canon = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', head, re.I)
    final = chain[-1]["url"] if chain else url
    return {"url": url, "status": status, "final_url": final,
            "noindex": "noindex" in xrt or bool(meta and "noindex" in meta.group(1).lower()),
            "canonical": canon.group(1) if canon else None}


def _parse_as_of(s):
    if not s:
        return None
    d = _parse_date(s)
    if not d:
        raise ValueError("--as-of must be YYYY-MM-DD")
    return d


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--validate", help="sitemap file path (.xml / .xml.gz) or raw XML")
    ap.add_argument("--crosscheck", help="sitemap file to gate against --pages")
    ap.add_argument("--pages", help="JSON list of page states for --crosscheck")
    ap.add_argument("--check-live", help="sitemap file: fetch a sample and gate it")
    ap.add_argument("--sample", type=int, default=25, help="URLs to fetch with --check-live")
    ap.add_argument("--urls", help="file of URLs (one per line) for --generate")
    ap.add_argument("--out", default="sitemap.xml")
    ap.add_argument("--lastmod", default=None, help="one ISO date for every URL (discouraged)")
    ap.add_argument("--lastmod-file", help="CSV 'url,YYYY-MM-DD' of real per-URL change dates")
    ap.add_argument("--base-url", default="", help="base URL for index child <loc> when splitting")
    ap.add_argument("--as-of", help="YYYY-MM-DD reference date for lastmod / news freshness")
    args = ap.parse_args(argv)

    try:
        as_of = _parse_as_of(args.as_of)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 1

    if args.validate:
        out = validate(args.validate, as_of)
    elif args.crosscheck:
        if not args.pages:
            print(json.dumps({"error": "--crosscheck needs --pages pages.json"}))
            return 1
        try:
            locs = sitemap_locs(args.crosscheck)
            with open(args.pages, encoding="utf-8") as fh:
                pages = json.load(fh)
        except (OSError, ValueError, ET.ParseError) as e:
            print(json.dumps({"error": f"could not load inputs: {e}"}))
            return 1
        out = crosscheck(locs, pages)
    elif args.check_live:
        try:
            locs = sitemap_locs(args.check_live)
        except (OSError, ValueError, ET.ParseError) as e:
            print(json.dumps({"error": f"could not read sitemap: {e}"}))
            return 1
        n = max(1, args.sample)
        pages = [_page_state(u) for u in locs[:n]]
        out = crosscheck(locs[:n], pages)
        out["pages"] = pages
        out["sampling"] = (f"fetched {min(n, len(locs))} of {len(locs)} sitemap URLs; "
                           "a full crawl needs Tier-1 (Firecrawl) or a larger --sample")
    elif args.generate:
        if not args.urls or not os.path.exists(args.urls):
            print(json.dumps({"error": "--generate needs --urls pointing to a file of URLs"}))
            return 1
        lastmods = None
        if args.lastmod_file:
            try:
                with open(args.lastmod_file, encoding="utf-8") as fh:
                    lastmods = {r.split(",")[0].strip(): r.split(",")[1].strip()
                                for r in fh if "," in r}
            except (OSError, IndexError) as e:
                print(json.dumps({"error": f"could not read --lastmod-file: {e}"}))
                return 1
        out = generate(_read_urls(args.urls), args.out, args.lastmod, args.base_url, lastmods)
    else:
        print("Use --generate, --validate, --crosscheck or --check-live.", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
