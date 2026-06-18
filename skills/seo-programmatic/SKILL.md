---
name: seo-programmatic
description: Programmatic SEO planning and safeguards for pages generated at scale — template design, URL patterns, internal-link automation, thin-content thresholds, and index-bloat prevention. Trigger when the user says "programmatic SEO", "pSEO", "pages at scale", "dynamic pages", "template pages", "generated pages", "data-driven SEO", or "scaled pages".
---

# seo-programmatic

**Family:** seo
**Status:** Stable

## Purpose

Plan SEO at template scale (city + service combos, product + use-case matrices) with
the safeguards that decide whether pSEO succeeds. Most pSEO fails not from technical
issues but from Google de-prioritizing thin, near-duplicate generated pages — the
thin-content safeguard is the differentiator.

## Triggers

- "programmatic seo" / "pSEO" / "data-driven seo"
- "pages at scale" / "scaled pages"
- "dynamic pages" / "template pages" / "generated pages"

## Inputs

- The template definition (variables + content sources)
- Expected page count and a few sample input rows
- Existing site context

## Steps

1. **Design the template** so each page carries genuinely unique value, not just a
   swapped noun — unique data, local specifics, real media per page.
2. **Simulate output** across the sample inputs and estimate the unique-content ratio;
   use `seo-content` to score representative pages for thinness.
3. **Set thin-content safeguards** — a minimum unique-content threshold; pages below
   it get `noindex` (or aren't generated). State the threshold explicitly.
4. **URL + canonical strategy** — slug conventions, parameter handling, and
   canonicalization so variants don't cannibalize.
5. **Internal-link automation** — rules for how generated pages interlink (to a hub,
   to siblings) with sensible anchor text; align to clusters via `seo-cluster`.
6. **Index-bloat plan** — decide which template pages Google should crawl vs.
   `noindex`; submit the worthy set via `seo-sitemap`.
7. **Render** the plan: template spec, thresholds, link rules, index strategy.

## Outputs

- Programmatic SEO plan with explicit unique-content thresholds
- Internal-link automation spec + URL/canonical strategy
- Index-management (crawl vs noindex) plan

## Dependencies

- `seo-content` (unique-content scoring), `seo-cluster` (keyword-template fit),
  `seo-sitemap` (index the worthy set)

## Notes

The thin-content threshold is the safeguard that keeps a pSEO project from getting
the whole template pattern devalued. Decide it before generating, not after.
