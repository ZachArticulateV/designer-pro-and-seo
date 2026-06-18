---
name: seo-technical
description: 9-category technical SEO audit — crawlability, indexability, security headers, URL structure, mobile, Core Web Vitals (LCP/CLS/INP), structured data, JavaScript rendering, and IndexNow/AI-crawler policy. Trigger when the user says "technical seo", "crawl issues", "robots.txt", "core web vitals", "site speed", "security headers", "indexability", "javascript seo", or "indexnow".
---

# seo-technical

**Family:** seo
**Status:** Stable

## Purpose

The technical spine of SEO. Runs scriptable on-page/technical checks on a URL (or
local HTML) and interprets them across 9 dimensions, deferring real field metrics
to `seo-google` and deep structured-data work to `seo-schema`.

Current standards it encodes: **Core Web Vitals targets LCP < 2.5s, CLS < 0.1,
INP < 200ms** (INP, not FID, is the metric — and the most-failed one); the 2026
robots.txt nuance of **blocking AI *training* crawlers (GPTBot, Google-Extended,
ClaudeBot) while allowing AI *retrieval* bots (OAI-SearchBot, PerplexityBot)** so
content stays citable; and **IndexNow** for instant change notification to
Bing/Yandex/AI engines.

## Triggers

- "technical seo" / "technical audit"
- "crawl issues" / "robots.txt"
- "core web vitals" / "site speed"
- "security headers" / "indexability"
- "javascript seo" / "indexnow"

## Inputs

- A URL (fetched) or a local HTML file (offline)
- Optional: a Google connection via `seo-google` for real CWV field data

## Steps

1. **Run the audit script:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/tech_audit.py" --url <URL> --human     # or --file page.html
   ```
   It checks title/meta, h1, canonical, meta-robots noindex, viewport, lang,
   structured-data presence, image alt coverage, mixed content, and — when it can
   fetch — security headers and the robots.txt AI-crawler policy.
2. **Interpret across the 9 dimensions:** crawlability (robots/sitemap),
   indexability (meta robots/canonical/noindex), security (HTTPS/HSTS/CSP/mixed
   content), URL structure, mobile (viewport/tap targets), CWV, structured data,
   JS rendering (is content visible without JS?), IndexNow/AI-crawler policy.
3. **Core Web Vitals:** the script emits the targets and flags that synthetic
   tools can't measure field CWV — if the user has Google access, pull real
   CrUX/PSI data via `seo-google`; otherwise report observable risks only.
4. **Structured data:** if missing/weak, hand to `seo-schema`.
5. **Render** per-dimension findings grouped Critical / High / Medium / Info, each
   with a specific fix.

## Outputs

- Per-dimension findings with prioritized fixes (script JSON or `--human` text)
- Cross-references to `seo-google` (field CWV) and `seo-schema` (structured data)
- An explicit AI-crawler policy recommendation for robots.txt

## Dependencies

- `scripts/seo/tech_audit.py` (required) — Python 3.10+, standard library only
- `seo-google` (optional — real CWV field data), `seo-schema` (deep structured data)

## Notes

The technical foundation; most other SEO findings assume this layer is healthy.
The script degrades gracefully offline (use `--file`).
