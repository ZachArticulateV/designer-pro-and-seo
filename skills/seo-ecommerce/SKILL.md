---
name: seo-ecommerce
description: Optimizes e-commerce SEO across product and category pages — on-page product elements, Product schema validation, image SEO, and faceted/canonical strategy for filters and variants. Uses DataForSEO Merchant for Google Shopping and Amazon marketplace intelligence when connected; otherwise audits feed basics and on-page signals manually. Trigger when the user says "ecommerce SEO", "product SEO", "product schema", "Google Shopping", "Amazon SEO", "marketplace SEO", "product listings", "shopping ads", or "merchant SEO".
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

1. **Run the product audit** on each key product page — merchant-listing eligibility
   *and* agreement between markup and the visible page:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/product_audit.py" --file product.html --url <URL> --as-of <YYYY-MM-DD> --human
   ```
   P1–P14: Product/ProductGroup markup validated through `schema_gen.py`, availability,
   GTIN/MPN/brand, return policy (Offer or Organization) and shipping details, expired
   `priceValidUntil`, **marked-up price not visible**, **rating markup with no visible
   rating**, **InStock vs "sold out"**, variants without a ProductGroup, H1, thin copy
   (`references/seo-ecommerce/merchant-checks.md`).
2. **Run the category audit** on listing, filtered and paginated URLs (pass the real
   URL with its query string):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/product_audit.py" --file list.html --url "<URL?color=red&page=2>" --type category --human
   ```
   C1–C6: self-canonical indexable facets, page N canonicalized to page 1, noindexed
   pagination, indexable sort URLs, thin category copy, ItemList.
3. **Image SEO** via `seo-image-audit` (product photos are conversion- and
   ranking-critical: alt, format, size, CLS).
4. **Faceted strategy** — decide which few facets deserve indexable landing pages
   (real demand + unique copy); canonicalize or noindex the rest (coordinate with
   `seo-programmatic`).
5. **Marketplace (optional).** If DataForSEO is configured, pull Google Shopping
   presence and Amazon/keyword-gap data; otherwise state what it would add and check
   feed basics manually.
6. **Render** per-product scores, schema validation, and a prioritized fix list.

## Outputs

- Per-product on-page scores + prioritized fixes
- Product schema validation report
- Marketplace presence/gap report (when DataForSEO present) or a manual checklist

## Dependencies

- `scripts/seo/product_audit.py` (required) — product + category audit (imports schema_gen)
- `references/seo-ecommerce/merchant-checks.md` (required) — codes, severities, scoring
- `seo-schema` (Product schema), `seo-page` (per-product), `seo-image-audit` (images)
- Optional: DataForSEO Merchant (Google Shopping/Amazon), `seo-programmatic` (facets)

## Notes

Conditional in `seo-audit` — fires on e-commerce signals (cart, checkout, Product
schema). Never fabricate ratings/reviews in schema — it's a manual action risk.
