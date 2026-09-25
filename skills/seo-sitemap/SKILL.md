---
name: seo-sitemap
description: Audits and generates sitemaps.org-compliant XML sitemaps and the internal-link architecture around them. Validates structure and honesty (protocol limits, hosts, duplicates, lastmod format/future/auto-bumped, image/video/news/hreflang extensions), runs quality gates (4xx, redirects, noindex, canonical-elsewhere, missing pages), maps the internal link graph (orphans, click depth, broken links, dead ends, generic anchors), and generates sitemaps with real per-URL lastmod. Trigger when the user says "sitemap", "XML sitemap", "generate sitemap", "validate sitemap", "sitemap issues", or "sitemap index".
---

# seo-sitemap

**Family:** seo
**Status:** Stable

## Purpose

Audit and generation for XML sitemaps. The script handles structure deterministically
(well-formed XML, the 50,000-URL / 50 MB protocol limits, automatic sitemap-index
splitting, absolute-URL checks); the skill layers the live quality gates that catch
the most common silent issues: URLs that 404, are noindexed, or canonicalize
elsewhere should never be in a sitemap.

## Triggers

- "sitemap" / "xml sitemap"
- "generate sitemap" / "sitemap index"
- "sitemap issues"

## Inputs

- A sitemap file/URL (audit), or a list of URLs (generate)
- Optional: base URL (for index child links) and a lastmod date

## Steps

1. **Validate structure + honesty** (`.xml` or `.xml.gz`; `--as-of` enables date checks):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/sitemap_tools.py" --validate sitemap.xml --as-of <YYYY-MM-DD>
   ```
   Protocol limits (50,000 URLs / 50 MB, absolute locs, root, namespace), host and
   scheme consistency, duplicates, fragments, tracking parameters, **lastmod honesty**
   (format, future dates, one date stamped on everything), ignored changefreq/priority,
   and the image / video / news / hreflang extensions. Codes S01–S26 and severities:
   `references/seo-sitemap/gates-and-architecture.md`.
2. **Run the quality gates** — a sitemap should list only 200, indexable,
   self-canonical URLs. With page states from a crawl or `tech_audit.py` runs:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/sitemap_tools.py" --crosscheck sitemap.xml --pages pages.json
   ```
   or let the script sample-fetch them through the shared SSRF guard (it states the
   sampling boundary):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/sitemap_tools.py" --check-live sitemap.xml --sample 25
   ```
   Gates G1–G5: 4xx/5xx, redirects, noindex, canonical-elsewhere, and indexable pages
   missing from the sitemap.
3. **Audit the internal-link architecture** against the sitemap — orphans, islands,
   click depth > 3, broken internal links, dead ends, nav-only and generic-anchor pages,
   internal nofollow:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/link_graph.py" --dir dist/ --base-url https://site.com --sitemap sitemap.xml --human
   ```
   (For a live site, feed a crawler's `{page: [links]}` export via `--edges`.)
4. **Generate** a fresh sitemap with real per-URL change dates:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/sitemap_tools.py" --generate --urls urls.txt --out sitemap.xml \
     --base-url https://site.com --lastmod-file lastmod.csv
   ```
   It dedupes, drops non-http(s) URLs, and splits into an index past 50,000 URLs.
5. **Robots:** confirm `robots.txt` has a `Sitemap:` directive (the AI-crawler verdict
   from `scripts/seo/ai_crawlers.py` lists the sitemaps it finds).

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`) and always produces a validated sitemap:

1. **Tier 1 — Firecrawl MCP.** When connected, crawl the live site to discover the
   true URL set (including JS-only pages) before validating or generating.
2. **Tier 2 — built-in (the default).** Otherwise `sitemap_tools.py` validates
   structure deterministically and generates a sitemaps.org-compliant file from a
   URL list, with `site_map.py` supplying the robots + sitemap-recursion inventory.
   Fully offline — this is the product.
3. **Tier 4 — guided.** If the URL set must come from a JS-rendered crawl and
   Firecrawl isn't connected, deliver the structural validation + generation and
   name what a full crawl would add.

```capability-routing
capability:   site-map
tier1:        Firecrawl MCP
tier1_signal: FIRECRAWL_API_KEY | FIRECRAWL_API_URL
tier2:        sitemap_tools.py (validate + crosscheck + generate) + link_graph.py (internal-link graph) + site_map.py (robots + sitemap recursion -> URL inventory)
tier2_yields: validated sitemaps.org-compliant sitemap + 404/noindex/canonical offender list, zero spend
tier3:        none
tier3_signal: none
tier4:        paste the sitemap or URL list; add a Firecrawl MCP to discover JS-only URLs for a full inventory
needs_tier1:  none
```

Always end by stating which tier ran and what a full crawl would add.

## Outputs

- Structure + honesty validation report with a score
- Quality-gate results (4xx / redirect / noindex / canonical-elsewhere / missing pages)
- Internal-link architecture report (orphans, depth, broken links, anchors) with a score
- Generated sitemap(s) + index for large sites

## Dependencies

- `scripts/seo/sitemap_tools.py` (required) — validate / crosscheck / check-live / generate
- `scripts/seo/link_graph.py` (required) — internal-link graph audit
- `scripts/seo/site_map.py` (required) — robots + sitemap-recursion URL inventory
- `references/seo-sitemap/gates-and-architecture.md` (required) — codes, gates, scoring

## Notes

The "no noindex, no canonical-elsewhere" gates catch the most common silent sitemap
issue. Structure is validated offline; the live gates need URL fetches.
