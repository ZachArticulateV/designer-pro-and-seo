#!/usr/bin/env python3
"""
tech_audit.py — single-page technical SEO checks (offline-friendly).

Reads a local HTML file or fetches a URL (urllib, short timeout) and reports on
the on-page technical signals: title/meta, h1, canonical, meta robots, viewport,
lang, structured-data presence, image alt coverage, and — when fetched —
security/response headers and a robots.txt AI-crawler policy read.

Encodes 2026 standards: Core Web Vitals targets LCP<2.5s / CLS<0.1 / INP<200ms
(INP is the most-failed metric — measure real field data with seo-google), and the
robots.txt nuance of blocking AI *training* crawlers while allowing AI *retrieval*
bots so content stays citable.

Cannot synthetically measure CWV (needs a real browser/field data) — it emits
guidance and defers to seo-google. Standard library only; degrades gracefully when
offline.

Usage:
  python3 tech_audit.py --url https://example.com
  python3 tech_audit.py --file page.html [--url https://example.com]   # url for https/headers context
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse, urljoin
from urllib.error import URLError, HTTPError

# --- shared SSRF guard (local sibling in scripts/workflow) -------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import (  # noqa: E402
    safe_open, validate_url, UrlValidationError, SafeFetchError,
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_crawlers  # noqa: E402  (shared AI-crawler registry + robots evaluator)

UA = "Mozilla/5.0 (compatible; designer-pro-seo-techaudit/1.0)"
TRAINING_BOTS = ai_crawlers.TRAINING_BOTS      # back-compat re-exports
RETRIEVAL_BOTS = ai_crawlers.RETRIEVAL_BOTS
SEC_HEADERS = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
}


def fetch(url, timeout=10):
    """Return (html, headers_dict, error). headers lowercased. Routed through the
    shared net_safety.safe_open, which validates the URL and EVERY redirect hop before
    fetching it -- a redirect to an internal IP / cloud-metadata host is refused like a
    direct one. Never raises; a blocked URL or transport failure returns an error."""
    try:
        resp, _chain = safe_open(url, timeout=timeout, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError) as e:
        return None, {}, str(e)
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, {}, str(e)
    try:
        status = getattr(resp, "status", None) or getattr(resp, "code", None)
        if status is not None and status >= 400:
            return None, {}, "HTTP %s" % status
        raw = resp.read(2_000_000).decode("utf-8", "replace")
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return raw, headers, None
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, {}, str(e)
    finally:
        try:
            resp.close()
        except Exception:
            pass


def fetch_robots(url, timeout=8):
    p = urlparse(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    raw, _, err = fetch(robots_url, timeout)
    return robots_url, raw, err


def _find(pattern, html, flags=re.I | re.S):
    m = re.search(pattern, html, flags)
    return m.group(1).strip() if m else None


def analyze_html(html, url=None):
    f = {"critical": [], "high": [], "medium": [], "info": []}

    title = _find(r"<title[^>]*>(.*?)</title>", html)
    if not title:
        f["critical"].append("Missing <title>")
    elif len(title) > 60:
        f["medium"].append(f"<title> is {len(title)} chars (>60 may truncate)")
    else:
        f["info"].append(f"title OK ({len(title)} chars)")

    desc = _find(r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']', html)
    if not desc:
        f["high"].append("Missing meta description")
    elif not (50 <= len(desc) <= 165):
        f["medium"].append(f"meta description is {len(desc)} chars (aim ~120-160)")
    else:
        f["info"].append(f"meta description OK ({len(desc)} chars)")

    h1s = re.findall(r"<h1[\s>]", html, re.I)
    if len(h1s) == 0:
        f["high"].append("No <h1> found")
    elif len(h1s) > 1:
        f["medium"].append(f"{len(h1s)} <h1> tags (prefer exactly 1)")
    else:
        f["info"].append("exactly one <h1>")

    canonical = _find(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']', html)
    if not canonical:
        f["medium"].append("No canonical link")
    else:
        f["info"].append(f"canonical: {canonical}")

    robots_meta = _find(r'<meta[^>]+name=["\']robots["\'][^>]*content=["\'](.*?)["\']', html)
    if robots_meta and "noindex" in robots_meta.lower():
        f["critical"].append(f'meta robots = "{robots_meta}" (page is NOINDEX)')
    elif robots_meta:
        f["info"].append(f"meta robots: {robots_meta}")

    if not re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I):
        f["high"].append("No responsive viewport meta (mobile usability)")
    else:
        f["info"].append("viewport meta present")

    lang = _find(r"<html[^>]*\blang=[\"'](.*?)[\"']", html)
    if not lang:
        f["medium"].append("No lang attribute on <html> (a11y + i18n)")
    else:
        f["info"].append(f"lang: {lang}")

    ld = re.findall(r'<script[^>]+type=["\']application/ld\+json["\']', html, re.I)
    if not ld:
        f["high"].append("No JSON-LD structured data found (use seo-schema)")
    else:
        f["info"].append(f"{len(ld)} JSON-LD block(s) present")

    imgs = re.findall(r"<img\b[^>]*>", html, re.I)
    no_alt = [i for i in imgs if not re.search(r'\balt=', i, re.I)]
    if imgs:
        if no_alt:
            f["medium"].append(f"{len(no_alt)}/{len(imgs)} <img> missing alt (use seo-image-audit)")
        else:
            f["info"].append(f"all {len(imgs)} images have alt")

    if re.search(r'(src|href)=["\']http://', html):
        f["high"].append("Mixed content: http:// resources on the page")

    return f


def analyze_headers(headers):
    f = []
    present = [SEC_HEADERS[h] for h in SEC_HEADERS if h in headers]
    missing = [SEC_HEADERS[h] for h in SEC_HEADERS if h not in headers]
    if missing:
        f.append({"severity": "medium", "msg": "Missing security headers: " + ", ".join(missing)})
    if present:
        f.append({"severity": "info", "msg": "Security headers present: " + ", ".join(present)})
    return f


def _agent_disallows_root(raw, bot):
    """True when robots.txt blocks `bot` from / (RFC 9309 group + longest-match
    precedence, via the shared ai_crawlers evaluator)."""
    groups, _ = ai_crawlers.parse_robots(raw)
    return ai_crawlers.bot_status(bot, groups, "/") == "blocked"


def analyze_robots(raw):
    notes = []
    v = ai_crawlers.verdict(raw)
    cls = v["classes"]
    sev = {"search-engine-blocked": "critical", "retrieval-blocked": "high",
           "retrieval-partial": "medium"}.get(v["verdict"], "info")
    named = sorted({b for c in cls.values() for b in c["explicitly_named"]})
    msg = "AI-crawler policy: %s -- %s" % (v["verdict"], v["note"])
    if not named and v["verdict"] == "fully-open":
        msg += (" robots.txt names no AI crawler: decide explicitly whether to block "
                "training (GPTBot/ClaudeBot/Google-Extended/CCBot) while keeping AI search "
                "(OAI-SearchBot/Claude-SearchBot/PerplexityBot) allowed. "
                "`ai_crawlers.py --generate citable-no-training` emits a ready block.")
    notes.append({"severity": sev, "msg": msg})
    if not v["sitemaps"]:
        notes.append({"severity": "medium", "msg": "robots.txt has no Sitemap: directive"})
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="page URL to fetch")
    ap.add_argument("--file", help="local HTML file (offline)")
    ap.add_argument("--no-network", action="store_true", help="never fetch")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args()

    report = {"target": args.url or args.file, "fetched": False, "findings": {},
              "headers": [], "robots": [], "cwv_guidance": {
                  "targets": {"LCP": "<2.5s", "CLS": "<0.1", "INP": "<200ms"},
                  "note": "INP is the most-failed CWV in 2026. Synthetic tools can't measure field CWV — use seo-google (CrUX/PSI) for real field data."},
              "indexnow": "Consider IndexNow to push URL changes to Bing/Yandex/AI engines instantly.",
              "errors": []}

    html = None
    if args.file:
        try:
            with open(args.file, encoding="utf-8", errors="replace") as fh:
                html = fh.read()
        except OSError as e:
            report["errors"].append(f"could not read file: {e}")
    if html is None and args.url and not args.no_network:
        if urlparse(args.url).scheme not in ("http", "https"):
            report["errors"].append("URL must be http(s)")
        else:
            html, headers, err = fetch(args.url)
            if err:
                report["errors"].append(f"fetch failed ({err}) — offline? pass --file to audit local HTML")
            else:
                report["fetched"] = True
                report["headers"] = analyze_headers(headers)
                _, rraw, rerr = fetch_robots(args.url)
                if rraw:
                    report["robots"] = analyze_robots(rraw)

    if args.url:
        report["https"] = urlparse(args.url).scheme == "https"
        if args.url and not report["https"]:
            report.setdefault("findings", {}).setdefault("critical", []).append("Not served over HTTPS")

    if html:
        f = analyze_html(html, args.url)
        # merge https critical if present
        for sev in ("critical", "high", "medium", "info"):
            report["findings"].setdefault(sev, [])
            report["findings"][sev] += f.get(sev, [])
    elif not report["errors"]:
        report["errors"].append("no HTML to analyze (provide --file or a reachable --url)")

    if args.human:
        print(f"# Technical audit: {report['target']}  (fetched={report['fetched']})")
        for sev in ("critical", "high", "medium", "info"):
            for msg in report["findings"].get(sev, []):
                print(f"[{sev.upper()}] {msg}")
        for h in report["headers"]:
            print(f"[{h['severity'].upper()}] {h['msg']}")
        for r in report["robots"]:
            print(f"[ROBOTS/{r['severity'].upper()}] {r['msg']}")
        print(f"[CWV] targets LCP<2.5s CLS<0.1 INP<200ms — {report['cwv_guidance']['note']}")
        for e in report["errors"]:
            print(f"[ERROR] {e}")
    else:
        print(json.dumps(report, indent=2))

    # Exit non-zero when no page content could be analyzed but an error was recorded
    # (missing --file, unreachable/invalid URL, no input) so callers and CI detect the
    # failure instead of reading an empty report as a clean pass. The gate keys off
    # whether real HTML was analyzed (no content -> `not html`, covering both a missing
    # file and an empty/unreadable one) — a synthetic, scheme-only finding like "Not
    # served over HTTPS" must not mask a bad-input failure. A successful audit (a read
    # page with content) has html set and exits 0.
    if not html and report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
