#!/usr/bin/env python3
"""
drift_tools.py — "git for SEO": baseline SEO-critical page elements, then diff.

Capture a JSON baseline of a page's SEO-critical elements, and later diff a fresh
capture against it to catch regressions a deploy silently introduced (title changed,
canonical flipped, noindex added, schema removed, word count gutted).

Standard library only. Deterministic; works offline on local HTML, or fetches a URL.

Usage:
  python3 drift_tools.py --capture --file page.html --out baseline.json [--url https://...]
  python3 drift_tools.py --diff --file page.html --baseline baseline.json
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

UA = "Mozilla/5.0 (compatible; designer-pro-seo-drift/1.0)"

# (key, severity if it changes/disappears)
SEVERITY = {
    "title": "high", "meta_description": "medium", "h1": "high",
    "canonical": "high", "meta_robots": "critical", "og_title": "low",
    "og_description": "low", "og_image": "medium", "schema_blocks": "high",
    "h2_count": "low", "word_count": "medium",
}


def _find(pat, html):
    m = re.search(pat, html, re.I | re.S)
    return m.group(1).strip() if m else None


def fetch(url, timeout=10):
    try:
        with urlopen(Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
            return r.read(2_000_000).decode("utf-8", "replace"), None
    except (URLError, HTTPError, ValueError, TimeoutError) as e:
        return None, str(e)


def capture(html, url=None):
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    words = len(text.split())
    return {
        "url": url,
        "title": _find(r"<title[^>]*>(.*?)</title>", html),
        "meta_description": _find(r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']', html),
        "h1": _find(r"<h1[^>]*>(.*?)</h1>", html),
        "canonical": _find(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']', html),
        "meta_robots": _find(r'<meta[^>]+name=["\']robots["\'][^>]*content=["\'](.*?)["\']', html),
        "og_title": _find(r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\'](.*?)["\']', html),
        "og_description": _find(r'<meta[^>]+property=["\']og:description["\'][^>]*content=["\'](.*?)["\']', html),
        "og_image": _find(r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\'](.*?)["\']', html),
        "schema_blocks": len(re.findall(r'application/ld\+json', html, re.I)),
        "h2_count": len(re.findall(r"<h2[\s>]", html, re.I)),
        "word_count": words,
    }


def diff(baseline, current):
    changes = []
    for key in SEVERITY:
        old, new = baseline.get(key), current.get(key)
        if old == new:
            continue
        sev = SEVERITY[key]
        # special-case the genuinely dangerous transitions
        if key == "meta_robots" and new and "noindex" in str(new).lower() and (not old or "noindex" not in str(old).lower()):
            sev = "critical"
        if key == "word_count" and isinstance(old, int) and isinstance(new, int):
            if old and abs(new - old) / max(1, old) < 0.15:
                continue  # ignore minor word-count noise
        changes.append({"element": key, "severity": sev, "before": old, "after": new})
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    changes.sort(key=lambda c: order.get(c["severity"], 9))
    return {"action": "diff", "changed": len(changes), "regressions": changes,
            "summary": ("no SEO drift detected" if not changes
                        else f"{len(changes)} element(s) changed since baseline")}


def _get_html(args):
    if args.file:
        try:
            with open(args.file, encoding="utf-8", errors="replace") as f:
                return f.read(), None
        except OSError as e:
            return None, "could not read --file %s: %s" % (args.file, e)
    if args.url and not args.no_network:
        if urlparse(args.url).scheme not in ("http", "https"):
            return None, "url must be http(s)"
        return fetch(args.url)
    return None, "provide --file or a reachable --url"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--file", help="local HTML")
    ap.add_argument("--url", help="page URL")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--out", default="baseline.json")
    ap.add_argument("--baseline", help="baseline JSON for --diff")
    args = ap.parse_args()

    html, err = _get_html(args)
    if err and not html:
        print(json.dumps({"error": err}))
        sys.exit(1)

    if args.capture:
        snap = capture(html, args.url)
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2)
        except OSError as e:
            print(json.dumps({"error": "could not write --out %s: %s" % (args.out, e)}))
            sys.exit(1)
        print(json.dumps({"action": "capture", "out": args.out, "captured": snap}, indent=2))
    elif args.diff:
        if not args.baseline or not os.path.exists(args.baseline):
            print(json.dumps({"error": "--diff needs --baseline pointing to a baseline JSON"}))
            sys.exit(1)
        try:
            with open(args.baseline, encoding="utf-8") as bf:
                base = json.load(bf)
        except (OSError, json.JSONDecodeError) as e:
            print(json.dumps({"error": "could not read baseline JSON %s: %s" % (args.baseline, e)}))
            sys.exit(1)
        print(json.dumps(diff(base, capture(html, args.url)), indent=2))
    else:
        print("Use --capture or --diff.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
