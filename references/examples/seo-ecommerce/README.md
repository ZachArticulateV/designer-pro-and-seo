# Golden example — seo-ecommerce (Tier-2: `product_audit.py`)

Proves the free, offline e-commerce audit: merchant-listing eligibility plus agreement
between the markup and what the page actually shows, and index hygiene for paginated
and filtered category URLs.

## Input

- `product.html`: a two-size product page (fictional brand) with realistic drift
  between the markup and the page:
  - an expired `priceValidUntil`
  - a 4.9★ rating in markup that the page never shows
  - `InStock` in markup while the page says "sold out"
  - $429 in markup vs $399 on the page
  - no return or shipping policy
  - two variants without a ProductGroup
- `category.html`: page 2 of a filtered listing whose canonical points at page 1.

## Commands

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/product_audit.py" --file references/examples/seo-ecommerce/product.html \
  --url https://example.test/p/classic-bench --as-of 2026-09-25 --human
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/product_audit.py" --file references/examples/seo-ecommerce/category.html \
  --url "https://example.test/benches?color=red&page=2" --human
```

## Expected free deliverable (Tier 2)

**Product: score 40/100.**
- High:
  - P8: expired offer
  - P9: price 429.00 not visible
  - P10: rating not visible
  - P11: InStock vs sold out
- Medium:
  - P4: no availability on the 5 ft offer
  - P6: no return policy
  - P7: no shipping details
  - P12: variants without a ProductGroup
  - P14: thin copy

**Category: score 86/100.**
- C2 (high): page 2 canonicalizes to page 1
- C4 (medium): thin copy
- C6 (info): no ItemList

Marketplace and Merchant Center data stay in `needs_tier1`. The codes are in
`references/seo-ecommerce/merchant-checks.md`, and `tests/test_hreflang_commerce.py`
pins both results.
