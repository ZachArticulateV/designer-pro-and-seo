---
name: seo-page
description: Single-URL SEO review — on-page elements, content quality, meta, schema, images, observable performance signals, and internal links in one pass (real Core Web Vitals field data when seo-google is connected). Lightweight alternative to seo-audit when only one page matters. Trigger when the user says "analyze this page", "check page SEO", "single URL", "check this page", "review this URL", or provides one specific URL.
---

# seo-page

**Family:** seo
**Status:** Stable

## Purpose

The single-page analyzer: the same on-page, meta, schema, image, and internal-link
checks as a full audit, scoped to one URL, plus observable performance issues —
real Core Web Vitals *field* data only when `seo-google` is connected. Cheaper to
run and easier to act on for spot checks, pre-publish reviews, and "is this page
good?" questions. The free path (fetch + parse + score) is the whole product; paid
APIs only add live ranking and field-performance context.

## Triggers

- "analyze this page" / "check this page" / "review this URL"
- "single URL SEO" / "check page SEO"
- "page-level analysis"

## Inputs

- A single URL (or local HTML file)
- Optional: target keyword(s) for relevance scoring

## Steps

1. **Fetch the page** (WebFetch, or `curl`-style retrieval of the raw HTML). For a
   local build, read the file directly.
2. **On-page & meta** — check: one descriptive `<title>` (≤ ~60 chars), meta
   description (~150–160 chars), exactly one `<h1>` and a logical heading order,
   canonical tag, meta robots, and Open Graph / Twitter card tags.
3. **Content quality** — word count vs topical depth, target-keyword presence in
   title/H1/early body (without stuffing), readability, and whether the page
   answers the likely search intent. (Hand to `seo-content` for deep E-E-A-T.)
4. **Schema** — detect JSON-LD; validate type appropriateness and required
   properties; flag rich-result eligibility. (Delegate deeper work to `seo-schema`.)
5. **Images** — alt text presence/quality, dimensions declared (CLS), modern
   formats (WebP/AVIF), and lazy-loading below the fold.
6. **Performance** — note render-blocking resources and obvious payload issues.
   If `seo-google` (PageSpeed/CrUX) is available, pull real LCP/CLS/INP; otherwise
   report observable issues and say field data needs `seo-google`.
7. **Internal links** — count, descriptive anchor text, and whether the page links
   to/within relevant site sections.
8. **Optional enrichment** — if the DataForSEO extension is configured, add live
   ranking/keyword context; otherwise state, in one line, what it would add.
9. **Render a compact report** — findings grouped Critical / High / Medium / Low,
   each with a specific fix.

## Outputs

- Page-level findings grouped by priority, each with a concrete fix
- A short "what paid data would add" note when running the free path

## Dependencies

- None required — the free path uses page fetch + parsing only
- Optional: `seo-schema` (deep schema), `seo-content` (deep E-E-A-T),
  `seo-google` (real CWV/field data), DataForSEO extension (ranking context)

## Notes

A focused single-page subset of `seo-audit`; both exist because their cost
profiles differ (one URL vs. a full crawl). They share the same checks — keep the
simple entry point (see `references/ENGINE-CONTRACTS.md` §5 on the free path).
