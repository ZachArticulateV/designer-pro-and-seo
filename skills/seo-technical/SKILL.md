---
name: seo-technical
description: 10-dimension technical SEO audit with a fix per finding and a deterministic lab score — crawlability (RFC 9309 AI-crawler policy, redirects), indexability (noindex / X-Robots-Tag, canonical conflicts, the 2 MB Googlebot index limit), security (true mixed content, headers), URL structure, mobile, Core Web Vitals lab risks (lazy LCP image, render-blocking scripts, CLS), structured data, JavaScript rendering (client-rendered shells), and SERP presentation. Trigger when the user says "technical seo", "crawl issues", "robots.txt", "core web vitals", "site speed", "security headers", "indexability", "javascript seo", or "indexnow".
---

# seo-technical

**Family:** seo
**Status:** Stable

## Purpose

The technical spine of SEO. Runs scriptable technical checks on a URL (or local HTML)
across 10 dimensions, attaches a concrete fix to every finding, and computes a
deterministic 0-100 **lab score** the audit orchestrator can weight — deferring real
field metrics to `seo-google` and deep structured-data work to `seo-schema`. The full
check catalog, severity rationale and score formula are in
`references/seo-technical/check-catalog.md`.

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
   Pass `--url` alongside `--file` to add URL-structure checks without fetching.
   Every finding is a `{dimension, severity, finding, fix}` record; the JSON also
   carries `score` (lab), per-dimension counts, and `needs_tier1`.
2. **Interpret across the 10 dimensions** (catalog:
   `references/seo-technical/check-catalog.md`): crawlability (AI-crawler policy via
   the shared `scripts/seo/ai_crawlers.py`, Sitemap directive, redirect hops),
   indexability (noindex incl. the `X-Robots-Tag` header, nosnippet, canonical
   missing / conflicting / relative / cross-host / noindex-conflict, 2 MB index limit,
   doctype, charset, lang, hreflang), security (HTTPS, true mixed content, headers),
   URL structure, mobile (viewport, zoom), CWV lab risks, structured data (presence,
   parse errors, retired types), JS rendering (client-rendered shell, JS-only links),
   SERP presentation (title, description, h1, Open Graph, alt), plus IndexNow
   guidance. Lead with criticals: a noindex, a blocked Googlebot, or a shell page
   outranks every medium.
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
   10-dimension lab audit offline (`--file` / `--no-network`) and emits the CWV
   targets — a complete, prioritized technical report on its own, no key, no
   network. This is the product.
3. **Tier 4 — guided.** If nothing is connected, deliver the lab audit and name the
   field-CWV gap, pointing to a free Google PSI/CrUX key via `seo-google`.

```capability-routing
capability:   cwv-field
tier1:        Google PSI / CrUX (free key) via seo-google
tier1_signal: CRUX_API_KEY | GOOGLE_API_KEY
tier2:        tech_audit.py (10-dimension lab audit + lab score + LCP<2.5 / CLS<0.1 / INP<200 targets, no key)
tier2_yields: prioritized per-dimension technical findings with concrete fixes, zero spend
tier3:        none
tier3_signal: none
tier4:        manual technical-SEO checklist; add a free Google PSI/CrUX key via seo-google for field CWV
needs_tier1:  field CWV (LCP/CLS/INP from CrUX), real Lighthouse performance score
```

Always end by stating which tier ran and what field data a higher tier would add.

## Outputs

- Per-dimension findings, each with a fix (script JSON or `--human` text)
- A deterministic lab score (0-100) with its basis stated, never a field-CWV number
- Cross-references to `seo-google` (field CWV) and `seo-schema` (structured data)
- An explicit AI-crawler policy recommendation for robots.txt

## Dependencies

- `scripts/seo/tech_audit.py` (required) — Python 3.10+, standard library only
- `scripts/seo/ai_crawlers.py` (required, imported) — shared RFC 9309 AI-crawler evaluator
- `references/seo-technical/check-catalog.md` (required) — checks, severities, score
- `references/shared/search-landscape-2026.md` (required) — dated facts the checks encode
- `seo-google` (optional — real CWV field data), `seo-schema` (deep structured data)

## Notes

The technical foundation; most other SEO findings assume this layer is healthy.
The script degrades gracefully offline (use `--file`).
