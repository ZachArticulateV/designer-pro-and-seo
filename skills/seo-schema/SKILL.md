---
name: seo-schema
description: Detect, validate, and generate Schema.org structured data in JSON-LD. Validates required properties per Google's rich-results rules and @id cross-references across pages (schema graph linking). Trigger when the user says "schema", "structured data", "rich results", "JSON-LD", "markup", "schema validation", or wants rich-results eligibility.
---

# seo-schema

**Family:** seo
**Status:** Stable

## Purpose

Full Schema.org JSON-LD lifecycle: detect what's present, validate against required
properties, generate appropriate markup for the page type, and check `@id`
cross-references across pages to form a coherent schema graph (a frequently-missed
dimension). JSON-LD is the only format Google recommends.

Encodes 2026 reality: active rich-result types include Article, Product,
Review/AggregateRating, Event, Organization, LocalBusiness, BreadcrumbList,
VideoObject — and **FAQPage rich results were deprecated on 2026-05-07** (still
valid schema and useful for AI/semantic context, but no longer a Google rich
result). The validator flags this so you don't promise a snippet that won't appear.

## Triggers

- "schema" / "structured data" / "rich results"
- "json-ld" / "markup"
- "validate schema" / "add schema" / "schema graph"

## Inputs

- Page URL or local file (detect/validate), or a page type + facts (generate)
- Mode: detect | validate | generate | graph-check

## Steps

1. **List supported types + their required props:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --list
   ```
2. **Detect / validate** existing markup (extract `application/ld+json` blocks from
   the page, then):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --validate markup.json
   ```
   Reports missing required + recommended properties and any deprecation warnings.
3. **Generate** the right type for the page (Article/Product/LocalBusiness/etc.):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --type Article --data '{"headline":"...","author":"...","datePublished":"2026-06-01"}'
   ```
   It auto-validates the result so you only ship complete markup. Use ISO 8601 for
   dates.
4. **Graph-check:** across multiple pages, verify `@id` references resolve
   (Organization ↔ WebSite ↔ Article author, BreadcrumbList positions) so the site
   reads as one entity graph, not disconnected snippets.
5. **Deliver** ready-to-drop JSON-LD `<script type="application/ld+json">` blocks
   and a validation summary.

## Outputs

- Inventory of existing schema, validation report (missing required/recommended)
- Generated, pre-validated JSON-LD blocks
- Cross-page `@id` graph linkage report
- Deprecation flags (e.g. FAQPage rich result)

## Dependencies

- `scripts/seo/schema_gen.py` (required) — Python 3.10+, standard library only

## Notes

Cross-page `@id` graph linking is frequently missed — most tools validate per-page
only. A hub for the SEO family (`seo-page`, `seo-technical`, `seo-local-unified`,
`seo-ecommerce` lean on it).
