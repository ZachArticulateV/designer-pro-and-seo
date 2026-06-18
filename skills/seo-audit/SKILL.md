---
name: seo-audit
description: Multi-specialist SEO audit orchestrator. Audits the URLs you provide (or a full-site crawl when seo-firecrawl is installed), detects business type, dispatches the available specialist skills, and aggregates a single weighted health score with prioritized findings. Trigger when the user says "seo audit", "full site audit", "analyze my site", "website health check", or "comprehensive seo review".
---

# seo-audit

**Family:** seo
**Status:** Stable

## Purpose

The orchestrator and public face of the SEO family. Runs the available specialist
skills against your target, then aggregates their findings into one weighted health
score with a prioritized fix list — so the user gets a single answer, not eight
disconnected reports.

Scope note (honest): it audits the **URLs you provide** out of the box. Full-site
crawling (up to ~500 pages, business-type auto-detect at scale) activates when the
`seo-firecrawl` skill is installed; without it, point it at the key URLs.

## Triggers

- "seo audit" / "full site audit" / "comprehensive seo review"
- "analyze my site for SEO" / "website health check"
- "audit [domain]"

## Inputs

- A domain, a URL, or a small list of key URLs
- Optional: business-type override; specialist include/exclude

## Steps

1. **Scope.** Take the URL(s). If `seo-firecrawl` is available, crawl to discover
   pages; otherwise audit the provided URLs and say so.
2. **Profile.** Infer business type (SaaS / e-commerce / local / publisher /
   agency) from the content to decide which conditional specialists apply.
3. **Dispatch the shipping specialists** (each one-directional, no back-edges):
   - `seo-page` — per-URL on-page review
   - `seo-technical` — technical dimensions (`tech_audit.py`)
   - `seo-schema` — structured-data validation
   - `seo-sitemap` — sitemap structure + gates
   - `seo-image-audit` — image SEO
   As more specialists ship (`seo-content`, `seo-geo`, `seo-google`,
   `seo-backlinks`, `seo-local-unified`, `seo-ecommerce`, …) they join here; until
   then, note which dimensions weren't covered rather than implying they were.
4. **Aggregate + score.** Weighted health score (0–100): Technical 30, On-page/
   content 30, Structured data 15, Images 10, Sitemap/crawl 15 (re-normalize over
   the specialists actually run, and report the weighting used).
5. **Prioritize.** Merge findings into one list: Critical → High → Medium → Low,
   deduped, each with the owning specialist and a specific fix.
6. **Render** the health score, the prioritized fix list, and per-specialist
   appendices. State explicitly which specialists ran and which were skipped.

## Outputs

- Weighted health score (0–100) with the weighting shown
- One prioritized, deduped fix list (Critical/High/Medium/Low)
- Per-specialist detail appendices + an explicit "covered / not covered" list

## Dependencies

- Shipping specialists: `seo-page`, `seo-technical`, `seo-schema`, `seo-sitemap`,
  `seo-image-audit`
- Optional: `seo-firecrawl` (full crawl), plus other `seo-*` specialists as they ship

## Notes

Most SEO requests should land here first; it routes to specialists. It never claims
coverage it didn't run — the "covered / not covered" list keeps the health score
honest.
