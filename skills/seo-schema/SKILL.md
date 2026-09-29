---
name: seo-schema
description: Detect, validate, and generate Schema.org structured data as JSON-LD. Extracts every ld+json block from HTML, validates nested values (offers, return policies, shipping, ratings) and value rules (ISO dates, absolute URLs, numeric price, ISO 4217 currency) against September 2026 rich-results rules, flags retired displays (FAQ, HowTo, the 2025 set) as info, scores the result, graph-checks @id references across pages, and emits a linked Organization/WebSite/WebPage starter graph. Trigger when the user says "schema", "structured data", "rich results", "JSON-LD", "schema markup", "validate schema", "schema graph", or "rich results eligibility".
---

# seo-schema

**Family:** seo
**Status:** Stable

## Purpose

Full Schema.org JSON-LD lifecycle: extract what's on the page, validate it (nested
values included), generate the right markup, and prove the site reads as **one entity
graph** — the part of structured data that keeps paying off for ranking systems and AI
answer engines even after a rich-result display is retired. JSON-LD is the only
format Google recommends.

Encodes the September 2026 status (dated in
`references/shared/search-landscape-2026.md` §5): active rich results include Product
/ merchant listings, Review snippets, Breadcrumb, Article, Video, Event, Recipe,
LocalBusiness, Organization, ProfilePage, DiscussionForumPosting and JobPosting;
**FAQ rich results ended on 2026-05-07**, HowTo and the sitelinks search box are gone,
and the 2025-retired set (Course Info, Claim Review, Estimated Salary, Learning Video,
Special Announcement, Vehicle Listing) plus practice problems are flagged as *info* —
valid markup, no visual, never an error. Rules, `@id` conventions and scoring:
`references/seo-schema/entity-graph.md`; type vocabulary:
`references/shared/schema-catalog.md`.

## Triggers

- "schema" / "structured data" / "rich results"
- "json-ld" / "markup"
- "validate schema" / "add schema" / "schema graph"

## Inputs

- Page HTML file(s) or URL content saved locally (detect/validate/graph), inline or
  file JSON-LD (validate), a page type + facts (generate), or brand + page facts
  (site starter)
- Mode: detect | validate | generate | graph-check | site-starter

## Steps

1. **List supported types** (required, one-of groups, recommended, rich status):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --list
   ```
2. **Detect + validate straight from HTML** — every `application/ld+json` block,
   `@graph` flattened, nested values (Offer, MerchantReturnPolicy, shipping, ratings,
   reviews) checked against their own spec, plus value rules (ISO 8601 dates, absolute
   URLs, numeric price, ISO 4217 currency, schema.org enums, rating bounds, breadcrumb
   order):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --html page.html --human
   ```
   (`--validate file.json` does the same for raw JSON-LD.) The JSON carries
   `detected`, `deprecations`, per-node `issues` `{type, severity, property, finding,
   fix}`, and a 0-100 `score`.
3. **Graph-check across pages** — pass the home page plus the pages under review:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --graph home.html product.html about.html --human
   ```
   Flags dangling `@id` references, one `@id` with conflicting types, a split
   Organization entity, and missing Organization/WebSite hubs. The check sees only the
   files passed — say which pages were in scope.
4. **Generate** — a single node, auto-validated:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --type Product --data '{"name":"...","image":"https://...","offers":{"@type":"Offer","price":"49.00","priceCurrency":"USD","availability":"https://schema.org/InStock"}}'
   ```
   or the linked site skeleton (Organization → WebSite → WebPage → BreadcrumbList with
   `#fragment` ids), validated and graph-checked in one pass:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --site '{"name":"...","url":"https://site","logo":"https://site/logo.png","page":{"url":"https://site/p","name":"...","breadcrumb":[["Home","https://site/"],["Page"]]}}' --human
   ```
   Only mark up facts visible on the page (prices, ratings, reviews).
5. **Deliver** ready-to-drop `<script type="application/ld+json">` blocks, the
   validation + graph summary with scores, and the fix list — never promising a
   retired rich result.

## Outputs

- Inventory of detected types + deprecations, per-node validation with fixes, score
- Generated, pre-validated JSON-LD (single node or linked site `@graph`)
- Cross-page `@id` entity-graph report (dangling / conflicting / split / missing hubs)

## Dependencies

- `scripts/seo/schema_gen.py` (required) — Python 3.10+, standard library only
- `references/seo-schema/entity-graph.md` (required) — @id conventions, value rules, scoring
- `references/shared/schema-catalog.md` (required) — type vocabulary
- `references/shared/search-landscape-2026.md` (required) — which rich results are live

## Notes

Cross-page `@id` graph linking is frequently missed — most tools validate per-page
only. A hub for the SEO family (`seo-page`, `seo-technical`, `seo-local-unified`,
`seo-ecommerce` lean on it).
