# Golden example — seo-schema (Tier-2: `schema_gen.py`)

Proves the free, fully offline Tier-2 of `seo-schema`: extract JSON-LD straight
from HTML, validate nested values against current rich-result rules, and check the
cross-page `@id` entity graph. No key, no network.

## Input

- `home.html`: a clean `@graph` with an `Organization` (`#organization`) that
  declares an org-level `MerchantReturnPolicy`, plus a `WebSite` whose `publisher`
  references the Organization by `@id`.
- `product.html`: a `Product` + `BreadcrumbList` `@graph` seeded with realistic
  defects, and a separate `FAQPage` block:
  - a relative `image` URL
  - an Offer with `price: "$349"`, `priceCurrency: "usd"`, and `availability: "in stock"`
  - breadcrumb positions 1 and 3
  - `brand` referencing a misspelled `@id` (`#org` instead of `#organization`)

## Commands

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --html references/examples/seo-schema/product.html --human
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --graph references/examples/seo-schema/home.html references/examples/seo-schema/product.html --human
```

(From the repo root during development, drop `${CLAUDE_PLUGIN_ROOT}/`.)

## Expected free deliverable (Tier 2)

**Validation of `product.html`: score 68/100** (100 − 2 high × 10 − 3 medium × 4):

- `Product: NOT ELIGIBLE`
  - `[HIGH]` price `"$349"` is not a plain number
  - `[HIGH]` priceCurrency `"usd"` is not ISO 4217
  - `[MEDIUM]` availability `"in stock"` is not a schema.org value
  - `[MEDIUM]` relative image URL
- `BreadcrumbList`: `[MEDIUM]` positions are not 1..N in order
- `FAQPage`: `[INFO]` retired rich result (FAQ ended 2026-05-07). The markup is kept,
  but it won't produce a rich result.

**Entity graph across both pages: score 90/100**

- `[HIGH]` dangling `@id` reference `https://example.test/#org`. The product's
  brand points at an entity that is defined nowhere, so the site reads as two
  disconnected graphs.

Every finding carries a fix. `tests/test_schema_gen.py` pins both scores.
