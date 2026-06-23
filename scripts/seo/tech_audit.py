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
import re
import sys
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

UA = "Mozilla/5.0 (compatible; designer-pro-seo-techaudit/1.0)"
TRAINING_BOTS = ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot", "Bytespider"]
RETRIEVAL_BOTS = ["OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "ChatGPT-User"]
SEC_HEADERS = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
}


def fetch(url, timeout=10):
    """Return (html, headers_dict, error). headers lowercased."""
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(2_000_000).decode("utf-8", "replace")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return raw, headers, None
    except (URLError, HTTPError, ValueError, TimeoutError) as e:
        return None, {}, str(e)


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
    """True when robots.txt blocks `bot` from / under group precedence: the bot's own
    User-agent group wins; otherwise the `*` group applies. A group blocks / when it
    has `Disallow: /` with no overriding `Allow: /`. This is a real block check, not a
    mere User-agent mention."""
    lines = [l.split("#", 1)[0].rstrip() for l in raw.splitlines()]
    groups, i, n = [], 0, len(lines)
    while i < n:
        if not re.match(r"\s*User-agent\s*:", lines[i], re.I):
            i += 1
            continue
        agents = []
        while i < n and re.match(r"\s*User-agent\s*:", lines[i], re.I):
            agents.append(lines[i].split(":", 1)[1].strip().lower())
            i += 1
        disallow_root = allow_root = False
        while i < n and not re.match(r"\s*User-agent\s*:", lines[i], re.I):
            d = re.match(r"\s*Disallow\s*:\s*(.*?)\s*$", lines[i], re.I)
            a = re.match(r"\s*Allow\s*:\s*(.*?)\s*$", lines[i], re.I)
            if d and d.group(1) == "/":
                disallow_root = True
            if a and a.group(1) == "/":
                allow_root = True
            i += 1
        groups.append((set(agents), disallow_root and not allow_root))
    bot = bot.lower()
    for agents, blocks in groups:   # a bot-specific group takes precedence over '*'
        if bot in agents:
            return blocks
    for agents, blocks in groups:   # otherwise the wildcard group applies
        if "*" in agents:
            return blocks
    return False


def analyze_robots(raw):
    notes = []
    blocked = [b for b in TRAINING_BOTS if _agent_disallows_root(raw, b)]
    referenced = [b for b in (TRAINING_BOTS + RETRIEVAL_BOTS)
                  if re.search(rf"User-agent:\s*{re.escape(b)}", raw, re.I)]
    if blocked:
        notes.append({"severity": "info",
                      "msg": "robots.txt blocks AI training crawlers from / (" + ", ".join(blocked)
                             + "). Confirm retrieval bots (OAI-SearchBot/PerplexityBot) stay allowed so content remains citable."})
    elif referenced:
        notes.append({"severity": "info",
                      "msg": "robots.txt references AI crawlers (" + ", ".join(referenced)
                             + ") but none are fully Disallowed from / -- verify the intended policy."})
    else:
        notes.append({"severity": "info",
                      "msg": "robots.txt does not reference AI training crawlers (GPTBot/Google-Extended/ClaudeBot). 2026 best practice: decide explicitly whether to block training while allowing retrieval bots (OAI-SearchBot/PerplexityBot) so content stays citable."})
    if "sitemap:" not in raw.lower():
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
