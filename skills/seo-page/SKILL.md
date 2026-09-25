---
name: seo-page
description: Single-URL SEO review — runs the technical audit and the content audit on one page (on-page elements, meta, E-E-A-T signals, readability, keyword placement, schema, images, lab performance risks, internal links) in one pass with two deterministic scores (real Core Web Vitals field data when seo-google is connected). Lightweight alternative to seo-audit when only one page matters. Trigger when the user says "analyze this page", "check page SEO", "single URL", "check this page", "review this URL", or provides one specific URL.
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
2. **On-page, meta & technical** — run the technical audit on the saved HTML (pass
   `--url` for URL-structure checks):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/tech_audit.py" --file page.html --url <URL> --no-network --human
   ```
   Title, meta description, one `<h1>`, canonical, meta robots / X-Robots-Tag, Open
   Graph, viewport, lab CWV risks, JS-rendering and mixed content — each with a fix
   (catalog: `references/seo-technical/check-catalog.md`).
3. **Content quality** — run the content audit with the target keyword:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/content_audit.py" --file page.html --url <URL> --keyword "<target>" --type <article|product|local|home|category> --human
   ```
   E-E-A-T signals (YMYL-aware), heading order, readability, depth for the page type,
   keyword placement / stuffing, in-content internal links and anchors, scaled-content
   tells, passage citability (rubric: `references/seo-content/content-rubric.md`).
   Then judge intent match by hand; hand deep E-E-A-T work to `seo-content`.
4. **Schema** — detect JSON-LD; validate type appropriateness and required
   properties; flag rich-result eligibility. (Delegate deeper work to `seo-schema`.)
5. **Images** — alt text presence/quality, dimensions declared (CLS), modern
   formats (WebP/AVIF), and lazy-loading below the fold.
6. **Performance** — note render-blocking resources and obvious payload issues.
   If `seo-google` (PageSpeed/CrUX) is available, pull real LCP/CLS/INP; otherwise
   report observable issues and say field data needs `seo-google`.
7. **Internal links** — the content audit counts in-content internal links and flags
   generic anchors; judge whether they point at the right hub and next step.
8. **Optional enrichment** — if the DataForSEO extension is configured, add live
   ranking/keyword context; otherwise state, in one line, what it would add.
9. **Render a compact report** — findings grouped Critical / High / Medium / Low,
   each with a specific fix.

## Outputs

- Page-level findings grouped by priority, each with a concrete fix
- Two deterministic scores — technical (lab) and content — plus the combined view
- A short "what paid data would add" note when running the free path

## Dependencies

- `scripts/seo/tech_audit.py` (required) — technical / on-page / lab-CWV checks
- `scripts/seo/content_audit.py` (required) — content quality, E-E-A-T signals, links
- `references/seo-content/content-rubric.md` (required) — content thresholds + scoring
- Optional: `seo-schema` (deep schema), `seo-content` (deep E-E-A-T),
  `seo-google` (real CWV/field data), DataForSEO extension (ranking context)

## Notes

A focused single-page subset of `seo-audit`; both exist because their cost
profiles differ (one URL vs. a full crawl). They share the same checks — keep the
simple entry point (see `references/ENGINE-CONTRACTS.md` §5 on the free path).
