#!/usr/bin/env python3
"""
sitemap_tools.py — XML sitemap generator + validator (sitemaps.org compliant).

Generate a sitemap (or a sitemap index when > 50,000 URLs) from a URL list, or
validate an existing sitemap's structure. Enforces the protocol limits: 50,000
URLs and 50 MB uncompressed per file.

Note: this validates STRUCTURE offline. Whether each URL returns 200 / isn't
noindexed / doesn't canonicalize elsewhere requires fetching them — the seo-sitemap
skill layers those live checks (via seo-page / a crawler) on top.

Standard library only.

Usage:
  # generate from a file of URLs (one per line)
  python3 sitemap_tools.py --generate --urls urls.txt --out sitemap.xml [--lastmod 2026-06-01]
  # validate an existing sitemap (file path or URL)
  python3 sitemap_tools.py --validate sitemap.xml
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

MAX_URLS = 50000
MAX_BYTES = 50 * 1024 * 1024
SM_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _read_urls(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def _esc(u):
    return (u.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))


def build_urlset(urls, lastmod=None):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<urlset xmlns="{SM_NS}">']
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{_esc(u)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
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


def generate(urls, out, lastmod=None, base_url=""):
    warnings = []
    bad = [u for u in urls if urlparse(u).scheme not in ("http", "https")]
    if bad:
        warnings.append(f"{len(bad)} URL(s) are not absolute http(s) — first: {bad[0]}")
    urls = [u for u in urls if urlparse(u).scheme in ("http", "https")]

    written = []
    if len(urls) <= MAX_URLS:
        xml = build_urlset(urls, lastmod)
        with open(out, "w", encoding="utf-8") as f:
            f.write(xml)
        written.append(out)
        size = os.path.getsize(out)
        if size > MAX_BYTES:
            warnings.append(f"{out} is {size//1024//1024}MB (> 50MB limit) — split it.")
    else:
        # split into chunks + an index
        stem, ext = os.path.splitext(out)
        chunks = [urls[i:i + MAX_URLS] for i in range(0, len(urls), MAX_URLS)]
        child_urls = []
        for idx, chunk in enumerate(chunks, 1):
            cpath = f"{stem}-{idx}{ext}"
            with open(cpath, "w", encoding="utf-8") as f:
                f.write(build_urlset(chunk, lastmod))
            written.append(cpath)
            loc = (base_url.rstrip("/") + "/" + os.path.basename(cpath)) if base_url else os.path.basename(cpath)
            child_urls.append(loc)
        with open(out, "w", encoding="utf-8") as f:
            f.write(build_index(child_urls, lastmod))
        written.insert(0, out)
        if not base_url:
            warnings.append("split into an index but no --base-url given; child <loc> are filenames, not absolute URLs — fix before deploy.")
    return {"action": "generate", "url_count": len(urls), "files": written, "warnings": warnings}


def validate(path_or_xml):
    warnings, errors = [], []
    # accept a file path, else treat as raw XML string
    if os.path.exists(path_or_xml):
        size = os.path.getsize(path_or_xml)
        if size > MAX_BYTES:
            warnings.append(f"file is {size//1024//1024}MB (> 50MB protocol limit)")
        with open(path_or_xml, encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = path_or_xml
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return {"action": "validate", "valid": False, "errors": [f"not well-formed XML: {e}"]}

    tag = root.tag.split("}")[-1]
    ns = "{" + SM_NS + "}"
    result = {"action": "validate", "root": tag, "valid": True, "errors": errors, "warnings": warnings}
    if tag == "urlset":
        locs = [e.text for e in root.iter(ns + "loc")]
        result["url_count"] = len(locs)
        if len(locs) > MAX_URLS:
            errors.append(f"{len(locs)} URLs (> 50,000 limit) — use a sitemap index")
        non_abs = [u for u in locs if not (u and urlparse(u).scheme in ("http", "https"))]
        if non_abs:
            errors.append(f"{len(non_abs)} <loc> are not absolute http(s)")
        if not locs:
            errors.append("urlset contains no <url> entries")
    elif tag == "sitemapindex":
        sms = [e.text for e in root.iter(ns + "loc")]
        result["sitemap_count"] = len(sms)
        if not sms:
            errors.append("sitemapindex contains no <sitemap> entries")
    else:
        errors.append(f"unexpected root <{tag}> (expected urlset or sitemapindex)")
    if root.tag.split("}")[0].strip("{") != SM_NS:
        warnings.append("namespace is not the sitemaps.org 0.9 schema")
    result["valid"] = not errors
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--validate", help="sitemap file path or raw XML")
    ap.add_argument("--urls", help="file of URLs (one per line) for --generate")
    ap.add_argument("--out", default="sitemap.xml")
    ap.add_argument("--lastmod", default=None, help="ISO date, e.g. 2026-06-01")
    ap.add_argument("--base-url", default="", help="base URL for index child <loc> when splitting")
    args = ap.parse_args()

    if args.validate:
        out = validate(args.validate)
    elif args.generate:
        if not args.urls or not os.path.exists(args.urls):
            print(json.dumps({"error": "--generate needs --urls pointing to a file of URLs"}))
            sys.exit(1)
        out = generate(_read_urls(args.urls), args.out, args.lastmod, args.base_url)
    else:
        print("Use --generate (with --urls) or --validate.", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
