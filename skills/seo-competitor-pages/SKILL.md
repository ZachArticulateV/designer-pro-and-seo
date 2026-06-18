---
name: seo-competitor-pages
description: Generate SEO-optimized competitor comparison and alternatives pages — "X vs Y" layouts, "alternatives to X" pages, feature matrices, schema, and conversion patterns. Trigger when the user says "comparison page", "vs page", "alternatives page", "competitor comparison", "X vs Y", "versus", "compare competitors", or "alternative to".
---

# seo-competitor-pages

**Family:** seo
**Status:** Stable

## Purpose

Generate the comparison and alternatives content types — bottom-of-funnel,
high-intent, often high-CTR pages that frequently outrank top-of-funnel content for
buyer-intent queries. Produces the page, its feature matrix, validated schema, and a
conversion-optimized layout.

## Triggers

- "comparison page" / "vs page" / "X vs Y" / "versus"
- "alternatives page" / "alternative to"
- "compare competitors" / "competitor comparison"

## Inputs

- Target product/service and the competitor(s) (user-named, or from provided pages)
- Page type: comparison ("X vs Y") | alternatives ("alternatives to X")
- Brand positioning / the honest angle you win on

## Steps

1. **Gather facts.** Use competitor pages the user provides (or `design-research`
   when available) to extract real feature/pricing data — never invent competitor
   facts (legal + trust risk).
2. **Build the matrix.** Score both sides on the criteria buyers actually weigh; be
   fair (one-sided hit pieces lose trust and links).
3. **Draft the page** (hand copy to `copywriting`): decisive H1, an at-a-glance
   verdict, the feature matrix, use-case fit ("choose X if…, choose Y if…"), and an
   FAQ section.
4. **Add schema** via `seo-schema`: Product/SoftwareApplication, Review/
   AggregateRating (only with real ratings), and BreadcrumbList. Note: FAQ markup is
   still valid for AI/semantic context but **no longer yields a Google rich result**
   (deprecated 2026-05-07) — don't promise an FAQ snippet.
5. **Conversion layer.** One primary CTA, decision-aid widget, trust signals near
   the verdict (apply `design-cro`).
6. **Render** the page (HTML/markdown) + the matrix data + embedded schema.

## Outputs

- Generated comparison/alternatives page (HTML or markdown)
- Feature-matrix data + validated JSON-LD
- Conversion-optimized layout notes

## Dependencies

- `seo-schema` (schema generation/validation); `copywriting` (page copy);
  `design-cro` (conversion). Optional: `design-research` (competitor facts).

## Notes

Accuracy and fairness are the differentiator and the legal guardrail — only publish
competitor claims you can substantiate.
