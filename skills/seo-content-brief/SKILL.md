---
name: seo-content-brief
description: Generate competitive SEO content briefs with per-section structure, word-count guidance, required entities, internal links, and schema recommendations. Supports new-page and improve-existing-page briefs. Trigger when the user says "content brief", "write a brief", "content outline", "blog brief", "service page brief", "brief for", "writing brief", or "outline for".
---

# seo-content-brief

**Family:** seo
**Status:** Stable

## Purpose

The production-planning side of content. Produces a brief a writer (or `content-draft`)
can execute: H1 + H2/H3 structure, per-section word-count guidance anchored on the
actual top-ranking pages, required entities/sub-topics, internal/external links, and
schema recommendations. Free path: analyze the competitor URLs you provide;
auto-SERP-fetch is the optional DataForSEO path.

## Triggers

- "content brief" / "write a brief" / "writing brief"
- "content outline" / "outline for" / "brief for [keyword]"
- "blog brief" / "service page brief"

## Inputs

- Target keyword(s) and page type (blog / service / pillar / comparison / glossary)
- Mode: new | improve (improve requires the existing URL)
- 3–10 top-ranking competitor URLs (or let DataForSEO fetch the SERP)
- Target audience

## Steps

1. **Gather the competition.** Use the provided top-ranking URLs (free path) or, if
   DataForSEO is configured, fetch the live SERP. Fetch each page's content.
2. **Extract patterns.** Common H2/H3 themes, entities/sub-topics every competitor
   covers, average and range of word counts per section, and any gaps none cover
   (your differentiation angle).
3. **Set the structure.** Recommend H1 + heading outline with a per-section word-count
   range (grounded in competitor averages, not a generic "1,500-word minimum").
4. **Specify requirements.** Required entities, internal links (to/from related
   pages), external authoritative citations, and schema (via `seo-schema`).
5. **Add citability guidance** — note where to place specific, sourced claims so the
   page is GEO-citable (see `seo-geo`).
6. **Render** the brief, paste-ready for a writer or `content-draft`. For improve
   mode, diff the existing page against the brief and list what to add/cut.

## Outputs

- Structured brief (markdown): outline, per-section word counts, entities, links, schema
- For improve mode: a gap list against the existing page

## Dependencies

- None required (free path uses provided competitor URLs)
- Optional: DataForSEO (auto-SERP), `seo-cluster` (related keywords), `seo-schema`
  (schema), `content-draft` (executes the brief)

## Notes

Per-section word counts grounded in real competitor scoring beat generic minimums.
Pairs with `content-draft` (writes it) and `seo-content` (audits the result).
