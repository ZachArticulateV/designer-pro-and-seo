# seo-schema — Entity Graph, Value Rules & Scoring

Durable knowledge behind `scripts/seo/schema_gen.py`. Knowledge, not steps. The type
vocabulary (required/recommended per type) is in `references/shared/schema-catalog.md`.
Which rich-result displays are live or retired is dated in
`references/shared/search-landscape-2026.md` §5.

## Why a graph, not snippets

Search engines and AI answer engines resolve markup into **entities**. Say one page
calls the business `#organization`, another `#org`, and a third embeds an anonymous
`Organization` blob. Then the site has asserted three different businesses. A graph
where every page points back to the same few hub nodes tells one consistent story.
That consistency is the part of structured data that still pays off after a
rich-result display is retired.

## @id conventions (the plugin's house rules)

| Entity | @id pattern | Defined on | Referenced from |
|---|---|---|---|
| Organization / LocalBusiness | `https://site/#organization` | home (or every page) | WebSite.publisher, WebPage.about, Article.publisher, Product.brand/manufacturer |
| WebSite | `https://site/#website` | home (or every page) | WebPage.isPartOf |
| WebPage | `<page-url>#webpage` | that page | Article.mainEntityOfPage |
| BreadcrumbList | `<page-url>#breadcrumb` | that page | WebPage.breadcrumb |
| Person (author) | `https://site/authors/<slug>#person` | the author's ProfilePage | Article.author |
| Product | `<page-url>#product` | the product page | Offer.itemOffered (if split) |

- **Absolute, fragment-style ids.** They are globally unique and never collide with a
  real URL's content.
- **One @id, one @type, everywhere.** If the same id carries two types, the graph
  check flags a conflict.
- **A reference is `{"@id": "…"}` and nothing else.** A reference must resolve to a
  node defined somewhere in the audited set. Otherwise it is *dangling* (high).

`schema_gen.py --site` emits the Organization → WebSite → WebPage → BreadcrumbList
skeleton wired with these ids, then validates and graph-checks its own output.

## Graph-check findings

| Finding | Severity | Why |
|---|---|---|
| Dangling `@id` reference | high | The link points at nothing, so the entity is lost |
| Same `@id`, conflicting types | medium | Ambiguous entity |
| Several distinct Organization ids | medium | The brand is split across entities |
| No Organization / LocalBusiness | medium | No hub to attach authorship, brand, reviews |
| No WebSite | info | Loses the site-name signal |
| Non-absolute `@id` | info | Collision risk across sites |

The graph check sees **only the files you pass**. A "dangling" reference to a node
defined on a page you didn't include is a scope artifact. Include the home page, or
say which pages were in scope.

## Value rules (beyond presence)

- **Dates:** ISO 8601 (`2026-09-25` or `2026-09-25T09:00:00+00:00`). `dateModified`
  must not predate `datePublished`, and should change only on real content edits.
- **URLs:** absolute `https://` for `url`, `image`, `logo`, `item`, `sameAs`,
  `contentUrl`, `thumbnailUrl` and similar.
- **Offers:** `price` is a plain number string or number (`349`, `49.99`) with no
  symbol or thousands comma. `priceCurrency` is ISO 4217 uppercase. `availability`
  and `itemCondition` use schema.org enum values.
- **Ratings:** `ratingValue` lies inside `worstRating..bestRating` (default 1..5), and
  counts are positive integers. Only mark up ratings users can see on the page.
- **Breadcrumbs:** positions run 1..N in order, and every crumb but the last has an
  `item` URL.
- **"One of" requirements:** a Product needs `offers`, `review` or `aggregateRating`.
  A JobPosting needs `jobLocation` or `applicantLocationRequirements`. A forum
  posting needs `text`, `image` or `video`.

## Merchant pattern (2026)

Declare returns once, on the Organization (`hasMerchantReturnPolicy` with
`applicableCountry` + `returnPolicyCategory` + `merchantReturnDays`). Override
per-Offer only where a product differs. Put variants in a `ProductGroup` with
`variesBy` + `hasVariant`, with each variant a full `Product` carrying its own `Offer`.

## Scoring

Every issue has a severity: **high** means not eligible or broken, **medium** is a
value defect, **info** is a recommended property, a retired display or an advisory.
The score is `max(0, 100 − 25·critical − 10·high − 4·medium)`: deterministic, and
built only from what the script observed. Retired rich-result types never cost points.
Accurate markup stays useful even when the visual is gone.
