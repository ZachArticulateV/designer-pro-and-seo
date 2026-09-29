# seo-ecommerce — Merchant-Listing Checks, Category Hygiene & Scoring

The durable knowledge behind `scripts/seo/product_audit.py`. Knowledge, not steps.
Product markup validation itself (required properties, value rules) comes from
`scripts/seo/schema_gen.py`. See `references/seo-schema/entity-graph.md` for the
merchant pattern and `references/shared/search-landscape-2026.md` §5 for rich-result
status.

## Product pages: what makes a listing eligible *and* trustworthy

Eligibility is the markup (name, image, an Offer with price + currency + availability).
Trust is **agreement**: the markup, the visible page and the Merchant Center feed must
state the same price, availability and rating. Disagreement is the classic manual-action
and listing-disapproval trigger, so the audit checks the page against its own markup.

| Code | Check | Severity |
|---|---|---|
| P1 | no Product / ProductGroup markup | high |
| P2 | Product markup not eligible (schema_gen high findings) | high |
| P3 | Product markup value defects (schema_gen medium findings) | medium |
| P4 | Offer without availability | medium |
| P5 | no GTIN / MPN and no brand | medium |
| P6 | no return policy (Offer, or once on the Organization) | medium |
| P7 | no shipping details | medium |
| P8 | `priceValidUntil` already past (with `--as-of`) | high |
| P9 | marked-up price not visible on the page (cents must match when present) | high |
| P10 | aggregateRating markup but neither the rating nor the count is visible | high |
| P11 | `InStock` in markup while the page says sold out / out of stock | high |
| P12 | several Product nodes with no ProductGroup (or a group without `variesBy`, info) | medium |
| P13 | no H1 | high |
| P14 | under 150 visible words (thin product copy) | medium |

**Variants.** Model size and color variants as one `ProductGroup` (`productGroupID`,
`variesBy`, `hasVariant`), with each variant a full Product and its own Offer. If each
variant has its own URL, each is self-canonical. If variants are selectors on one URL,
the group lives on that URL.

**Returns and shipping.** Declare the return policy once on the Organization. Add
per-Offer overrides only where a product differs. Shipping details (rate, destination,
handling + transit time) sit on the Offer. Both feed the price/delivery annotations
shoppers see.

## Category and faceted pages: keep the index lean

| Code | Check | Severity |
|---|---|---|
| C1 | filtered URL (`?color=red`) is self-canonical and indexable | medium |
| C2 | page N (N > 1) canonicalizes to page 1 | high |
| C3 | paginated page is noindex | medium |
| C4 | under 80 visible words | medium |
| C5 | sort-order URL (`?sort=`) is indexable | medium |
| C6 | no ItemList markup | info |

- **Facets.** Every filter combination creates a URL. Index only the few with real
  search demand, as deliberate landing pages with unique copy. Canonicalize or noindex
  the rest, and never link crawlers into infinite combinations.
- **Pagination.** Google ignores `rel=next/prev`. Each page in the series is
  self-canonical and indexable, so the products on page 7 remain reachable.
  Canonicalizing everything to page 1 hides them.
- **Tracking parameters** (`utm_*`, `gclid`, …) are ignored when detecting facets.

## What the free path can't see

Merchant Center feed diagnostics, Google Shopping and marketplace visibility, and
competitor pricing are Tier-1 (DataForSEO Merchant, Merchant Center). They are listed
under `needs_tier1`, never estimated.

## Scoring and worked examples (pinned by `tests/test_hreflang_commerce.py`)

Scoring is `max(0, 100 − 25·critical − 10·high − 4·medium)` per finding type.

**`references/examples/seo-ecommerce/product.html` scores 40/100.**
- **High ×4:**
  - P8: the 4 ft offer expired 2026-06-30
  - P9: the markup says 429.00 but the page shows $399
  - P10: a 4.9★ / 212-review rating that appears nowhere on the page
  - P11: the 4 ft offer is `InStock` but the page says "sold out"
- **Medium ×5:**
  - P4: no availability on the 5 ft offer
  - P6: no return policy
  - P7: no shipping details
  - P12: two size variants without a ProductGroup
  - P14: 37 words of copy

**`category.html` at `?color=red&page=2` scores 86/100.**
- C2 (high): page 2 canonicalizes to page 1
- C4 (medium): thin copy
- C6 (info): no ItemList markup
