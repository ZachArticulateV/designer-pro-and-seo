#!/usr/bin/env python3
"""
tech_audit.py — single-page technical SEO audit across 10 dimensions (offline-friendly).

Reads a local HTML file or fetches a URL (SSRF-guarded, short timeout) and reports
every observable technical signal, each tagged with a dimension, a severity, and a
concrete fix:

  crawlability      robots.txt AI-crawler policy (shared ai_crawlers evaluator),
                    Sitemap directive, redirect chain length
  indexability      meta robots / X-Robots-Tag (noindex, nosnippet), canonical
                    (missing, multiple, relative, cross-host, noindex conflict),
                    Googlebot's 2 MB uncompressed index limit, doctype, charset, lang,
                    hreflang presence
  security          HTTPS, true mixed content (sub-resources only), security headers
  url-structure     length, case, underscores, query parameters, session ids
  mobile            viewport present, zoom not disabled
  cwv               LAB heuristics only: render-blocking head scripts, lazy-loaded
                    likely-LCP image, images without dimensions (CLS), missing
                    fetchpriority, oversized inline script/JSON
  structured-data   JSON-LD presence, parse errors, retired rich-result types
  js-rendering      client-rendered shell detection, JS-only links
  serp-presentation title / meta description / h1 / Open Graph
  indexnow          guidance only (not observable from one page)

Also emits a deterministic 0-100 LAB score (penalties per severity) so the seo-audit
orchestrator can fan the result in. The score is computed only from signals this
script actually observed — never a synthesized field CWV number (that stays in
`needs_tier1`, served by seo-google via CrUX/PSI).

Dated facts it encodes (see references/shared/search-landscape-2026.md): CWV targets
LCP<2.5s / INP<200ms / CLS<0.1; Googlebot indexes the first 2 MB of uncompressed HTML;
AI-search crawlers do not execute JavaScript; FAQ/HowTo rich results are retired.

Standard library only; degrades gracefully when offline.

Usage:
  python3 tech_audit.py --url https://example.com [--human]
  python3 tech_audit.py --file page.html [--url https://example.com] [--no-network]
"""
import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError

# --- shared SSRF guard (local sibling in scripts/workflow) -------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import (  # noqa: E402
    safe_open, validate_url, UrlValidationError, SafeFetchError,
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_crawlers  # noqa: E402  (shared AI-crawler registry + robots evaluator)
import schema_gen  # noqa: E402  (retired rich-result types — one source of truth)

UA = "Mozilla/5.0 (compatible; designer-pro-seo-techaudit/1.1)"
TRAINING_BOTS = ai_crawlers.TRAINING_BOTS      # back-compat re-exports
RETRIEVAL_BOTS = ai_crawlers.RETRIEVAL_BOTS
SEC_HEADERS = {
    "strict-transport-security": "HSTS",
    "content-security-policy": "CSP",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
}

DIMENSIONS = ("crawlability", "indexability", "security", "url-structure", "mobile",
              "cwv", "structured-data", "js-rendering", "serp-presentation", "indexnow")
SEVERITIES = ("critical", "high", "medium", "info")
PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}

INDEX_LIMIT_BYTES = 2 * 1024 * 1024        # Googlebot: first 2 MB of uncompressed HTML
INDEX_WARN_BYTES = 1024 * 1024
INLINE_SCRIPT_WARN = 100 * 1024
SHELL_WORDS = 60
SPA_ROOT_IDS = {"root", "app", "__next", "__nuxt", "svelte", "___gatsby", "main-app"}
SUBRESOURCE_ATTRS = {"img": "src", "script": "src", "iframe": "src", "source": "src",
                     "video": "src", "audio": "src", "embed": "src"}


# --- fetch --------------------------------------------------------------------

def fetch_ex(url, timeout=10):
    """Return (html, headers_dict, redirect_chain, error). headers lowercased. Routed
    through net_safety.safe_open, which validates the URL and EVERY redirect hop before
    fetching it. Never raises; a blocked URL or transport failure returns an error."""
    try:
        resp, chain = safe_open(url, timeout=timeout, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError) as e:
        return None, {}, getattr(e, "chain", []), str(e)
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, {}, [], str(e)
    try:
        status = getattr(resp, "status", None) or getattr(resp, "code", None)
        if status is not None and status >= 400:
            return None, {}, chain, "HTTP %s" % status
        raw = resp.read(INDEX_LIMIT_BYTES * 2).decode("utf-8", "replace")
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return raw, headers, chain, None
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, {}, chain, str(e)
    finally:
        try:
            resp.close()
        except Exception:
            pass


def fetch(url, timeout=10):
    """Back-compat 3-tuple (html, headers, error)."""
    html, headers, _chain, err = fetch_ex(url, timeout)
    return html, headers, err


def fetch_robots(url, timeout=8):
    p = urlparse(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    raw, _, err = fetch(robots_url, timeout)
    return robots_url, raw, err


# --- HTML collection ------------------------------------------------------------

class _Collector(HTMLParser):
    """One pass over the document collecting every fact the checks need."""

    _SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.doctype = False
        self.in_head = True
        self.html_lang = None
        self.titles, self._title_buf, self._in_title = [], [], False
        self.metas, self.links, self.imgs, self.anchors = [], [], [], []
        self.scripts = []            # {"attrs", "in_head", "inline_len"}
        self._script = None
        self.subresources = []       # (tag, url)
        self.h1 = 0
        self.ids = set()
        self.words = 0
        self._skip_depth = 0

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if a.get("id"):
            self.ids.add(a["id"].lower())
        if tag == "html" and a.get("lang"):
            self.html_lang = a["lang"]
        elif tag == "body":
            self.in_head = False
        elif tag == "title":
            self._in_title, self._title_buf = True, []
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
            if "stylesheet" in a.get("rel", "").lower() and a.get("href"):
                self.subresources.append(("link", a["href"]))
        elif tag == "img":
            a["_index"] = len(self.imgs)
            self.imgs.append(a)
        elif tag == "a":
            self.anchors.append(a)
        elif tag == "h1":
            self.h1 += 1
        if tag in ("h1", "h2", "h3", "p", "main", "article", "section") and self.in_head:
            self.in_head = False     # body content without an explicit <body>
        if tag == "script":
            self._script = {"attrs": a, "in_head": self.in_head, "inline_len": 0}
            self.scripts.append(self._script)
        if tag in SUBRESOURCE_ATTRS and a.get(SUBRESOURCE_ATTRS[tag]):
            self.subresources.append((tag, a[SUBRESOURCE_ATTRS[tag]]))
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self.titles.append("".join(self._title_buf).strip())
            self._in_title = False
        elif tag == "head":
            self.in_head = False
        if tag == "script":
            self._script = None
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)
            return
        if self._script is not None:
            self._script["inline_len"] += len(data)
            return
        if self._skip_depth == 0 and not self.in_head:
            self.words += len(data.split())


def _meta(c, name):
    """content of the first <meta name=|property=NAME>."""
    for m in c.metas:
        if m.get("name", "").lower() == name or m.get("property", "").lower() == name:
            return m.get("content", "")
    return None


def _ld_blocks(html):
    return re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                      html, re.I | re.S)


def _ld_types(node, out):
    if isinstance(node, dict):
        t = node.get("@type")
        for x in (t if isinstance(t, list) else [t]):
            if isinstance(x, str):
                out.append(x)
        for v in node.values():
            _ld_types(v, out)
    elif isinstance(node, list):
        for v in node:
            _ld_types(v, out)


# --- the audit ------------------------------------------------------------------

class _Report:
    def __init__(self):
        self.checks = []

    def add(self, sev, dim, finding, fix=None):
        self.checks.append({"dimension": dim, "severity": sev, "finding": finding,
                            "fix": fix or ""})

    def legacy(self):
        f = {s: [] for s in SEVERITIES}
        for c in self.checks:
            f[c["severity"]].append(c["finding"])
        return f


def analyze_html(html, url=None, headers=None):
    """Audit one HTML document. Returns the legacy severity->messages dict with the
    structured records under f["checks"] (dimension/severity/finding/fix)."""
    r = _Report()
    c = _Collector()
    try:
        c.feed(html)
        c.close()
    except Exception as e:  # html.parser is tolerant; this is belt-and-braces
        r.add("medium", "indexability", "HTML could not be fully parsed (%s)" % e,
              "Validate the markup; unclosed tags can hide content from parsers.")
    headers = headers or {}
    page_host = urlparse(url).netloc.lower() if url else ""
    is_https = (urlparse(url).scheme == "https") if url else None

    # ---- serp-presentation ------------------------------------------------------
    title = c.titles[0] if c.titles else ""
    if not title:
        r.add("critical", "serp-presentation", "Missing <title>",
              "Add a unique, descriptive <title> that front-loads the page topic.")
    else:
        if len(c.titles) > 1:
            r.add("high", "serp-presentation", "%d <title> tags" % len(c.titles),
                  "Keep exactly one <title>; templates often inject a second.")
        if len(title) > 60:
            r.add("medium", "serp-presentation",
                  f"<title> is {len(title)} chars (>60 may truncate)",
                  "Tighten to ~50-60 chars (~600 px); lead with the primary topic.")
        elif len(title) < 15:
            r.add("medium", "serp-presentation", f"<title> is only {len(title)} chars",
                  "Short titles get rewritten; describe the page in 30-60 chars.")
        else:
            r.add("info", "serp-presentation", f"title OK ({len(title)} chars)")

    desc = _meta(c, "description")
    if not desc:
        r.add("high", "serp-presentation", "Missing meta description",
              "Write a ~120-160 char summary that matches the query intent.")
    elif not (50 <= len(desc) <= 165):
        r.add("medium", "serp-presentation", f"meta description is {len(desc)} chars (aim ~120-160)",
              "Rewrite to ~120-160 chars; one clear value statement.")
    else:
        r.add("info", "serp-presentation", f"meta description OK ({len(desc)} chars)")

    if c.h1 == 0:
        r.add("high", "serp-presentation", "No <h1> found",
              "Add one visible <h1> stating the page topic.")
    elif c.h1 > 1:
        r.add("medium", "serp-presentation", f"{c.h1} <h1> tags (prefer exactly 1)",
              "Demote secondary headings to <h2>.")
    else:
        r.add("info", "serp-presentation", "exactly one <h1>")

    missing_og = [p for p in ("og:title", "og:description", "og:image") if not _meta(c, p)]
    if missing_og:
        r.add("medium", "serp-presentation", "Open Graph incomplete: missing " + ", ".join(missing_og),
              "Add og:title / og:description / og:image (1200x630) for share previews "
              "and AI surfaces that read OG.")
    else:
        r.add("info", "serp-presentation", "Open Graph title/description/image present")

    # ---- indexability -------------------------------------------------------------
    size = len(html.encode("utf-8"))
    if size > INDEX_LIMIT_BYTES:
        r.add("critical", "indexability",
              f"HTML is {size/1048576:.1f} MB uncompressed; Googlebot indexes only the first 2 MB",
              "Move inline JSON/SVG/base64 out of the HTML and paginate giant lists so "
              "real content sits inside the first 2 MB.")
    elif size > INDEX_WARN_BYTES:
        r.add("medium", "indexability",
              f"HTML is {size/1048576:.1f} MB uncompressed (limit 2 MB)",
              "Trim inline hydration state / SVG before content drifts past the 2 MB cutoff.")

    robots_vals = []
    for m in c.metas:
        if m.get("name", "").lower() in ("robots", "googlebot"):
            robots_vals.append(m.get("content", "").lower())
    xrt = headers.get("x-robots-tag", "").lower()
    if xrt:
        robots_vals.append(xrt)
    joined = ",".join(robots_vals)
    noindex = "noindex" in joined or "none" in [v.strip() for v in joined.split(",")]
    if noindex:
        src = "X-Robots-Tag header" if "noindex" in xrt else "meta robots"
        r.add("critical", "indexability", f'{src} = "{joined}" (page is NOINDEX)',
              "Remove noindex if this page should rank; keep it only for deliberate exclusions.")
    elif robots_vals:
        r.add("info", "indexability", "meta robots: " + joined)
    if "nosnippet" in joined or re.search(r"max-snippet\s*:\s*0\b", joined):
        r.add("medium", "indexability",
              "nosnippet / max-snippet:0 set -- no snippet and no AI Overview / AI Mode use",
              "Remove unless opting out of snippets and AI answers is intentional.")

    canon = [l.get("href", "") for l in c.links
             if "canonical" in l.get("rel", "").lower().split()]
    if not canon:
        r.add("medium", "indexability", "No canonical link",
              "Add a self-referencing absolute rel=canonical.")
    else:
        if len(canon) > 1 and len(set(canon)) > 1:
            r.add("high", "indexability", "%d conflicting canonical links" % len(canon),
                  "Emit exactly one canonical; conflicting ones are ignored.")
        cu = urlparse(canon[0])
        if not cu.scheme:
            r.add("medium", "indexability", f"canonical is relative: {canon[0]}",
                  "Use an absolute https:// URL for rel=canonical.")
        elif page_host and cu.netloc.lower() != page_host:
            r.add("medium", "indexability", f"canonical points to another host ({cu.netloc})",
                  "Confirm the cross-domain canonical is intentional (syndication).")
        if noindex:
            r.add("high", "indexability", "noindex combined with rel=canonical (mixed signals)",
                  "Pick one: noindex to drop the page, or canonical to consolidate it.")
        r.add("info", "indexability", f"canonical: {canon[0]}")

    if not c.doctype:
        r.add("medium", "indexability", "No <!DOCTYPE html> (quirks mode)",
              "Start the document with <!DOCTYPE html>.")
    if not any(m.get("charset") for m in c.metas) and "charset" not in \
            headers.get("content-type", "").lower() and not any(
            "charset" in m.get("content", "").lower() for m in c.metas):
        r.add("medium", "indexability", "No character encoding declared",
              'Add <meta charset="utf-8"> as the first element in <head>.')
    if not c.html_lang:
        r.add("medium", "indexability", "No lang attribute on <html> (a11y + i18n)",
              'Set <html lang="..."> to the page language.')
    else:
        r.add("info", "indexability", f"lang: {c.html_lang}")

    hl = [l for l in c.links if l.get("hreflang")]
    if hl:
        codes = {l["hreflang"].lower() for l in hl}
        msg = f"{len(hl)} hreflang alternate(s)"
        if "x-default" not in codes:
            r.add("info", "indexability", msg + " without x-default",
                  "Add an x-default alternate; validate the full cluster with seo-hreflang.")
        else:
            r.add("info", "indexability", msg + " incl. x-default (validate with seo-hreflang)")

    # ---- mobile ----------------------------------------------------------------------
    vp = _meta(c, "viewport")
    if vp is None:
        r.add("high", "mobile", "No responsive viewport meta (mobile usability)",
              'Add <meta name="viewport" content="width=device-width, initial-scale=1">.')
    else:
        v = vp.lower().replace(" ", "")
        m = re.search(r"maximum-scale=([\d.]+)", v)
        if "user-scalable=no" in v or "user-scalable=0" in v or (m and float(m.group(1)) < 2):
            r.add("medium", "mobile", "viewport disables pinch-zoom",
                  "Drop user-scalable=no / maximum-scale<2 (WCAG 1.4.4 resize text).")
        else:
            r.add("info", "mobile", "viewport meta present")

    # ---- structured-data -------------------------------------------------------------
    blocks = _ld_blocks(html)
    if not blocks:
        r.add("high", "structured-data", "No JSON-LD structured data found (use seo-schema)",
              "Add Organization/WebSite + the page's primary type as JSON-LD (seo-schema).")
    else:
        types, bad = [], 0
        for b in blocks:
            try:
                _ld_types(json.loads(b), types)
            except ValueError:
                bad += 1
        if bad:
            r.add("high", "structured-data", f"{bad} JSON-LD block(s) do not parse",
                  "Fix the JSON syntax; an invalid block is ignored entirely.")
        r.add("info", "structured-data", f"{len(blocks)} JSON-LD block(s) present"
              + (" -- types: " + ", ".join(sorted(set(types))) if types else ""))
        retired = sorted({t for t in types if schema_gen.SPEC.get(t, {}).get("deprecated_rich")})
        if retired:
            r.add("info", "structured-data", "retired rich-result type(s): " + ", ".join(retired),
                  "Keep the markup (valid machine context) but expect no rich result.")

    # ---- security --------------------------------------------------------------------
    insecure_sub = [u for _, u in c.subresources if u.lower().startswith("http://")]
    if insecure_sub and is_https is not False:
        r.add("high", "security", "Mixed content: http:// resources on the page",
              "Serve every image/script/stylesheet/iframe over https:// (%d found)."
              % len(insecure_sub))
    insecure_links = [a for a in c.anchors if a.get("href", "").lower().startswith("http://")]
    if insecure_links:
        r.add("info", "security", f"{len(insecure_links)} link(s) point to http:// URLs",
              "Link to the https:// version to skip a redirect hop.")

    # ---- cwv (lab heuristics) -------------------------------------------------------------
    blocking = [s for s in c.scripts if s["in_head"] and s["attrs"].get("src")
                and "async" not in s["attrs"] and "defer" not in s["attrs"]
                and s["attrs"].get("type", "").lower() != "module"]
    if blocking:
        r.add("medium", "cwv", f"{len(blocking)} render-blocking <script> in <head> (lab)",
              "Add defer (or async for independent scripts) so HTML parsing isn't blocked (LCP).")
    content_imgs = [i for i in c.imgs if i.get("src") or i.get("srcset")]
    if content_imgs:
        first = content_imgs[0]
        if first.get("loading", "").lower() == "lazy":
            r.add("high", "cwv", "First (likely LCP) image is loading=lazy (lab)",
                  "Remove loading=lazy from the hero/LCP image and add fetchpriority=high.")
        if not any(i.get("fetchpriority", "").lower() == "high" for i in content_imgs):
            r.add("info", "cwv", "No image carries fetchpriority=high",
                  "Mark the LCP image fetchpriority=high so it downloads first.")
        nodim = [i for i in content_imgs if not (i.get("width") and i.get("height"))
                 and "aspect-ratio" not in i.get("style", "").lower()]
        if nodim:
            r.add("medium", "cwv", f"{len(nodim)}/{len(content_imgs)} <img> without width/height (CLS risk, lab)",
                  "Set width+height (or CSS aspect-ratio) so space is reserved before load.")
    big_inline = [s for s in c.scripts if not s["attrs"].get("src")
                  and s["inline_len"] > INLINE_SCRIPT_WARN]
    if big_inline:
        kb = max(s["inline_len"] for s in big_inline) // 1024
        r.add("medium", "cwv", f"Inline script/JSON up to {kb} KB (parse cost + index-size risk)",
              "Ship hydration state as a cacheable file or trim it; keep inline JS small (INP).")

    # ---- js-rendering ----------------------------------------------------------------
    has_js = any(s["attrs"].get("src") or s["inline_len"] for s in c.scripts
                 if "ld+json" not in s["attrs"].get("type", "").lower())
    root = sorted(SPA_ROOT_IDS & c.ids)
    if has_js and ((root and c.words < SHELL_WORDS) or c.words < SHELL_WORDS // 3):
        r.add("high", "js-rendering",
              f"Only {c.words} words of server-rendered text"
              + (f" (app root #{root[0]})" if root else "") + " -- likely a client-rendered shell",
              "Server-render or prerender the main content; AI-search crawlers and most "
              "assistants do not execute JavaScript.")
    else:
        r.add("info", "js-rendering", f"{c.words} words of server-rendered text")
    js_links = [a for a in c.anchors if not a.get("href") or
                a.get("href", "").lower().startswith("javascript:")]
    if js_links:
        r.add("medium", "js-rendering", f"{len(js_links)} <a> without a crawlable href",
              "Use real <a href> URLs; onclick/javascript: links are not followed.")

    # image alt coverage (hand off detail to seo-image-audit)
    if c.imgs:
        no_alt = [i for i in c.imgs if "alt" not in i]
        if no_alt:
            r.add("medium", "serp-presentation",
                  f"{len(no_alt)}/{len(c.imgs)} <img> missing alt (use seo-image-audit)",
                  "Describe each meaningful image in alt; use alt=\"\" for decoration.")
        else:
            r.add("info", "serp-presentation", f"all {len(c.imgs)} images have alt")

    # ---- url-structure ---------------------------------------------------------------
    if url:
        analyze_url(url, r)

    f = r.legacy()
    f["checks"] = r.checks
    return f


def analyze_url(url, r):
    p = urlparse(url)
    path = p.path or "/"
    if len(url) > 115:
        r.add("medium", "url-structure", f"URL is {len(url)} chars",
              "Shorten to a readable slug (under ~115 chars).")
    if re.search(r"[A-Z]", path):
        r.add("medium", "url-structure", "URL path contains uppercase",
              "Use lowercase paths; mixed case creates duplicate URLs.")
    if "_" in path:
        r.add("info", "url-structure", "URL path uses underscores",
              "Prefer hyphens as word separators in new URLs (don't redirect old ones just for this).")
    params = [q for q in p.query.split("&") if q]
    if re.search(r"(^|&)(sid|sessionid|phpsessid|jsessionid)=", p.query, re.I):
        r.add("high", "url-structure", "Session id in the URL",
              "Move sessions to cookies; session URLs explode duplicate content.")
    elif len(params) > 2:
        r.add("medium", "url-structure", f"{len(params)} query parameters",
              "Canonicalize parameter variants to the clean URL.")


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


def lab_score(checks):
    """Deterministic 0-100 lab score from observed findings only."""
    return max(0, 100 - sum(PENALTY[c["severity"]] for c in checks))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="page URL to fetch (or context for --file)")
    ap.add_argument("--file", help="local HTML file (offline)")
    ap.add_argument("--no-network", action="store_true", help="never fetch")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args()

    report = {"target": args.url or args.file, "fetched": False, "findings": {},
              "checks": [], "score": None,
              "score_basis": "lab: 100 minus 25/critical, 10/high, 4/medium over observed "
                             "signals; not field CWV",
              "headers": [], "robots": [], "redirects": [],
              "cwv_guidance": {
                  "targets": {"LCP": "<2.5s", "CLS": "<0.1", "INP": "<200ms"},
                  "note": "INP is the most-failed CWV in 2026. Synthetic tools can't measure field CWV — use seo-google (CrUX/PSI) for real field data."},
              "indexnow": "Consider IndexNow to push URL changes to participating engines "
                          "(Bing, Yandex, Seznam, Naver); Google does not use it.",
              "needs_tier1": ["field CWV (LCP / INP / CLS p75 from CrUX)"],
              "errors": []}

    html, headers = None, {}
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
            html, headers, chain, err = fetch_ex(args.url)
            report["redirects"] = [h.get("url") for h in chain]
            if err:
                report["errors"].append(f"fetch failed ({err}) — offline? pass --file to audit local HTML")
            else:
                report["fetched"] = True
                report["headers"] = analyze_headers(headers)
                _, rraw, _ = fetch_robots(args.url)
                if rraw:
                    report["robots"] = analyze_robots(rraw)

    extra = []
    if args.url and urlparse(args.url).scheme != "https":
        extra.append({"dimension": "security", "severity": "critical",
                      "finding": "Not served over HTTPS",
                      "fix": "Serve the site over HTTPS and 301 http:// to https://."})
    if len(report["redirects"]) > 2:
        extra.append({"dimension": "crawlability", "severity": "medium",
                      "finding": f"{len(report['redirects']) - 1} redirect hops before the page",
                      "fix": "Link and canonicalize straight to the final URL (one hop max)."})
    for h in report["headers"]:
        extra.append({"dimension": "security", "severity": h["severity"],
                      "finding": h["msg"], "fix": ""})
    for rb in report["robots"]:
        extra.append({"dimension": "crawlability", "severity": rb["severity"],
                      "finding": rb["msg"], "fix": ""})

    if html:
        f = analyze_html(html, args.url, headers)
        checks = extra + f.pop("checks")
        report["checks"] = checks
        report["findings"] = {s: [c["finding"] for c in checks if c["severity"] == s]
                              for s in SEVERITIES}
        report["score"] = lab_score(checks)
        report["dimensions"] = {d: {s: sum(1 for c in checks if c["dimension"] == d
                                           and c["severity"] == s) for s in SEVERITIES}
                                for d in DIMENSIONS}
    else:
        for c in extra:
            report["findings"].setdefault(c["severity"], []).append(c["finding"])
        if not report["errors"]:
            report["errors"].append("no HTML to analyze (provide --file or a reachable --url)")

    if args.human:
        head = f"# Technical audit: {report['target']}  (fetched={report['fetched']})"
        if report["score"] is not None:
            head += f"  lab score {report['score']}/100"
        print(head)
        for sev in SEVERITIES:
            for c in report["checks"]:
                if c["severity"] != sev:
                    continue
                tag = "ROBOTS/" if c["dimension"] == "crawlability" and "AI-crawler" in c["finding"] else ""
                print(f"[{tag}{sev.upper()}] ({c['dimension']}) {c['finding']}")
                if c["fix"] and sev != "info":
                    print(f"    fix: {c['fix']}")
        print(f"[CWV] targets LCP<2.5s CLS<0.1 INP<200ms — {report['cwv_guidance']['note']}")
        for e in report["errors"]:
            print(f"[ERROR] {e}")
    else:
        print(json.dumps(report, indent=2))

    # Exit non-zero when no page content could be analyzed but an error was recorded
    # (missing --file, unreachable/invalid URL, no input) so callers and CI detect the
    # failure instead of reading an empty report as a clean pass. A synthetic,
    # scheme-only finding like "Not served over HTTPS" must not mask a bad-input failure.
    if not html and report["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
