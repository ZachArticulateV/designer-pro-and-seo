---
name: seo-ecommerce
description: E-commerce SEO — product-page on-page optimization, Product schema validation, image SEO, and (optionally) Google Shopping/Amazon marketplace intelligence. Trigger when the user says "ecommerce SEO", "product SEO", "Google Shopping", "marketplace SEO", "product schema", "Amazon SEO", "product listings", "shopping ads", or "merchant SEO".
---

# seo-ecommerce

**Family:** seo
**Status:** Stable

## Purpose

E-commerce-specific SEO. The free path fully covers on-page product SEO and Product
schema; marketplace intelligence (Google Shopping, Amazon) is the optional
DataForSEO-Merchant path.

## Triggers

- "ecommerce seo" / "product seo" / "merchant seo"
- "product schema" / "product listings"
- "google shopping" / "shopping ads" / "amazon seo" / "marketplace seo"

## Inputs

- Domain or product URL(s)
- Marketplace coverage (Google Shopping / Amazon / both / none)
- Competitor domains (optional)

## Steps

1. **Audit product pages** (free path): unique, benefit-led titles + descriptions;
   one h1; descriptive URL; internal links to category/related; review content
   present. Run `seo-page` per key product.
2. **Validate Product schema** via `seo-schema`: require `name` + `image`; for
   merchant eligibility include `offers` with `price` + `priceCurrency` +
   `availability`, plus `aggregateRating`/`review` **only when real**.
3. **Image SEO** via `seo-image-audit` (product photos are conversion- and
   ranking-critical: alt, format, size, CLS).
4. **Category/faceted strategy** — canonical handling for filters/sort, thin-variant
   consolidation (coordinate with `seo-programmatic`).
5. **Marketplace (optional).** If DataForSEO is configured, pull Google Shopping
   presence and Amazon/keyword-gap data; otherwise state what it would add and check
   feed basics manually.
6. **Render** per-product scores, schema validation, and a prioritized fix list.

## Outputs

- Per-product on-page scores + prioritized fixes
- Product schema validation report
- Marketplace presence/gap report (when DataForSEO present) or a manual checklist

## Dependencies

- `seo-schema` (Product schema), `seo-page` (per-product), `seo-image-audit` (images)
- Optional: DataForSEO Merchant (Google Shopping/Amazon), `seo-programmatic` (facets)

## Notes

Conditional in `seo-audit` — fires on e-commerce signals (cart, checkout, Product
schema). Never fabricate ratings/reviews in schema — it's a manual action risk.
