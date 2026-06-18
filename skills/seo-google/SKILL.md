---
name: seo-google
description: Real Google field data — Search Console (impressions/clicks/CTR/position, URL Inspection, sitemaps), PageSpeed Insights, CrUX field CWV, GA4 organic — when a Search Console MCP or Google APIs are connected; otherwise runs built-in on-page technical + GEO checks and tells you exactly what to connect for field data. Trigger when the user says "search console", "GSC", "PageSpeed", "PSI", "CrUX", "field data", "indexing API", "GA4 organic", "URL inspection", "real CWV data", "impressions", "clicks", "CTR", "LCP", "INP", "CLS".
---

# seo-google

**Family:** seo
**Status:** Stable

## Purpose

The "real field data" layer for the SEO family — Google's own measurements of how
real users experience a site, versus the synthetic/lab heuristics in `seo-technical`.
It is **tool-aware**: when a Google Search Console MCP (or Google APIs) is connected
it returns true field data; when nothing is connected it still delivers a real
on-page technical + GEO read and names precisely what to connect to unlock field
data. It never just fails.

What field data adds when connected:
- **Search Console** — impressions, clicks, CTR, average position; URL Inspection;
  sitemap status
- **PageSpeed Insights / CrUX** — real-user Core Web Vitals (LCP, INP, CLS), with
  CrUX's multi-week history
- **GA4** — organic traffic, engagement, conversions

## Triggers

- "search console" / "GSC"
- "pagespeed" / "PSI"
- "crux" / "field data" / "real CWV data"
- "indexing api" / "URL inspection"
- "ga4 organic" / "ga4 seo"
- "LCP" / "INP" / "CLS" / "FCP" / "TTFB"
- "impressions" / "clicks" / "CTR" / "position"

## Inputs

- Domain or page URL
- Which signal is wanted (search analytics | URL inspection | field CWV | organic traffic)
- Optional: date range / comparison window

## Steps

1. **Detect available tooling.** Run `scripts/workflow/capability_probe.py` (env
   keys) and check whether a Search Console / Google MCP is exposed this session.
2. **Field-data path (Tier 1, if connected).** Call the connected GSC/Google MCP or
   Google APIs for the requested signal; normalize into a compact table; for CrUX,
   overlay the available history.
3. **Built-in path (Tier 2, always available).** Fetch the page with WebFetch and
   run `scripts/seo/tech_audit.py` (on-page technical: title/meta, canonical, robots,
   viewport, structured-data presence, security headers, INP<200ms guidance) and
   `scripts/seo/geo_check.py` (AI-citability + llms.txt). This is real, useful output
   on its own — it just isn't *field* data.
4. **Report which tier ran** and, if field data wasn't available, the one-line setup
   to unlock it (connect a Search Console MCP, or set Google API OAuth).

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`):

1. **Tier 1 — Google data.** If a Search Console / Google MCP or Google APIs are
   connected, use them for true field data (GSC analytics, CrUX CWV, GA4 organic).
2. **Tier 2 — built-in (default).** Otherwise WebFetch + `tech_audit.py` +
   `geo_check.py` for an on-page technical + GEO read. Lab/heuristic, not field.
3. **Tier 4 — guided.** If a request strictly needs field data (e.g. impressions)
   and no Google tool is connected, deliver the built-in read and name the exact
   setup to unlock the field metric.

Always state which tier ran and what connecting Google would add.

## Outputs

- The requested signal as a compact table (field data when Tier 1; on-page +
  GEO findings when Tier 2)
- For CWV: the metric with its target (LCP<2.5s / CLS<0.1 / INP<200ms) and, on
  Tier 1, real-user values
- A one-line "to unlock field data, connect …" note when running built-in

## Dependencies

- Optional (Tier 1): a Google Search Console MCP, or Google APIs via OAuth — adds
  real field data; free path below works without them
- Built-in (Tier 2): WebFetch; `scripts/seo/tech_audit.py`; `scripts/seo/geo_check.py`
- `scripts/workflow/capability_probe.py` (capability detection)

## Notes

When connected, this is the field-data source of truth the rest of the SEO family
defers to for "is this actually a problem for real users?" `seo-technical` covers
the synthetic/lab side. Related: `seo-geo` (AI-citability depth).
