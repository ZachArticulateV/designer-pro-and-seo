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
from urllib.error import URLError, HTTPError

# --- shared SSRF guard (local sibling in scripts/workflow) -------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import (  # noqa: E402
    safe_open, validate_url, UrlValidationError, SafeFetchError,
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_crawlers  # noqa: E402  (AI-crawler verdict for the robots drift rule)

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
    """SSRF-guarded GET via the shared net_safety.safe_open (validates the URL and every
    redirect hop before fetching). Never raises; returns (text, None) or (None, error)."""
    try:
        resp, _chain = safe_open(url, timeout=timeout, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError) as e:
        return None, str(e)
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, str(e)
    try:
        status = getattr(resp, "status", None) or getattr(resp, "code", None)
        if status is not None and status >= 400:
            return None, "HTTP %s" % status
        return resp.read(2_000_000).decode("utf-8", "replace"), None
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, str(e)
    finally:
        try:
            resp.close()
        except Exception:
            pass


def capture(html, url=None, robots=None):
    """Snapshot the on-page SEO elements. When `robots` (robots.txt text) is supplied the
    snapshot also records the site's AI-crawler verdict (shared ai_crawlers evaluator) so
    drift can catch a deploy that silently blocks search engines or AI-search crawlers."""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    words = len(text.split())
    snap = {
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
    if robots is not None:
        snap["ai_crawler_verdict"] = ai_crawlers.verdict(robots)["verdict"]
    return snap


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


def load_html(file=None, url=None, no_network=False):
    """Public, SSRF-guarded HTML loader shared by the drift baseline/compare engines.

    Reads a local `--file`, or fetches `--url` through `fetch()` (which routes the
    request via the shared `net_safety.safe_open` guard — never a raw urlopen, and
    every redirect hop is re-validated). Returns `(html, error)`; never raises.
    drift_tools stays the one canonical element capturer + fetcher for the family."""
    if file:
        try:
            with open(file, encoding="utf-8", errors="replace") as f:
                return f.read(), None
        except OSError as e:
            return None, "could not read --file %s: %s" % (file, e)
    if url and not no_network:
        if urlparse(url).scheme not in ("http", "https"):
            return None, "url must be http(s)"
        return fetch(url)
    return None, "provide --file or a reachable --url"


def _get_html(args):
    return load_html(args.file, args.url, args.no_network)


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
