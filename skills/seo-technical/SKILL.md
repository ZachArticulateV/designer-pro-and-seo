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
ClaudeBot) while allowing AI *search* bots (OAI-SearchBot, Claude-SearchBot,
PerplexityBot) and user-triggered fetchers** so content stays citable — judged by the
shared RFC 9309 evaluator `scripts/seo/ai_crawlers.py`, which also flags a blocked
Googlebot/Bingbot as critical (that removes AI Overviews / AI Mode visibility too);
and **IndexNow** for instant change notification to participating engines (Bing,
Yandex, Seznam, Naver — not Google). Dated facts (2 MB index limit, rich-result
retirements, crawler classes) come from `references/shared/search-landscape-2026.md`.

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

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`) and always returns a usable audit:

1. **Tier 1 — Google PSI / CrUX (free key, via `seo-google`).** When a Google key
   is set, pull real *field* Core Web Vitals (LCP/CLS/INP) to harden the CWV
   dimension; a connected Firecrawl MCP can additionally JS-render shells for the
   "visible without JS?" check.
2. **Tier 2 — built-in (the default).** Otherwise `tech_audit.py` runs the full
   9-category lab audit offline (`--file` / `--no-network`) and emits the CWV
   targets — a complete, prioritized technical report on its own, no key, no
   network. This is the product.
3. **Tier 4 — guided.** If nothing is connected, deliver the lab audit and name the
   field-CWV gap, pointing to a free Google PSI/CrUX key via `seo-google`.

```capability-routing
capability:   cwv-field
tier1:        Google PSI / CrUX (free key) via seo-google
tier1_signal: CRUX_API_KEY | GOOGLE_API_KEY
tier2:        tech_audit.py (9-category lab audit + LCP<2.5 / CLS<0.1 / INP<200 targets, no key)
tier2_yields: prioritized per-dimension technical findings with concrete fixes, zero spend
tier3:        none
tier3_signal: none
tier4:        manual technical-SEO checklist; add a free Google PSI/CrUX key via seo-google for field CWV
needs_tier1:  field CWV (LCP/CLS/INP from CrUX), real Lighthouse performance score
```

Always end by stating which tier ran and what field data a higher tier would add.

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
