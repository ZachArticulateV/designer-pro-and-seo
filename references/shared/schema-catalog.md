# Schema.org Catalog — Types the Plugin Emits & Validates

Shared reference for the structured-data skills (`seo-schema`, `seo-page`,
`seo-local-unified`, `seo-ecommerce`, `seo-audit`). It catalogs the common
Schema.org types the plugin generates or checks, with the properties that matter
for rich results. The generator/validator lives in
`scripts/seo/schema_gen.py`; this file is the vocabulary reference it implements
against. JSON-LD is the preferred serialization. Knowledge, not steps.

## How to read this catalog

- **Required** = omit it and the markup is invalid / ineligible for the rich
  result.
- **Recommended** = strongly improves eligibility or display; include when the
  data exists.
- Properties are referenced from the public Schema.org vocabulary and Google's
  public rich-result guidance; their text is not redistributed here.

## Core entity & navigation types

| Type | Required | Recommended |
|---|---|---|
| **Organization** | `name` | `url`, `logo`, `sameAs`, `contactPoint` |
| **WebSite** | `name`, `url` | `alternateName` (site-name signal). `SearchAction` is harmless but no longer yields a sitelinks search box (feature removed) |
| **WebPage** | `name` | `url`, `description`, `breadcrumb`, `primaryImageOfPage` |
| **BreadcrumbList** | `itemListElement` (ordered `ListItem`s with `position`, `name`, `item`) | — |

## Content types

| Type | Required | Recommended |
|---|---|---|
| **Article / BlogPosting / NewsArticle** | `headline` | `image`, `datePublished`, `dateModified`, `author` (Person/Organization), `publisher` |
| **FAQPage** | `mainEntity` → `Question` each with an `acceptedAnswer` | — (note the reduced rich-result eligibility below) |
| **HowTo** | `name`, `step` (`HowToStep`s) | `image`, `totalTime`, `supply`, `tool` — valid schema, **no rich result** (display removed) |
| **VideoObject** | `name`, `thumbnailUrl`, `uploadDate` | `description`, `duration`, `contentUrl` / `embedUrl` |

## Commerce types

| Type | Required | Recommended |
|---|---|---|
| **Product** | `name` | `image`, `description`, `brand`, `sku`, `offers`, `aggregateRating`, `review` |
| **Offer** | `price`, `priceCurrency` | `availability`, `priceValidUntil`, `url`, `itemCondition` |
| **AggregateRating** | `ratingValue`, `reviewCount` (or `ratingCount`) | `bestRating`, `worstRating` |
| **Review** | `reviewRating` (→ `Rating.ratingValue`), `author` | `datePublished`, `reviewBody` |

## Merchant, community & profile types (2026 additions)

| Type | Required | Recommended |
|---|---|---|
| **ProductGroup** | `name` | `productGroupID`, `variesBy`, `hasVariant` (each a full `Product` + `Offer`) |
| **MerchantReturnPolicy** | `applicableCountry`, `returnPolicyCategory` | `merchantReturnDays`, `returnMethod`, `returnFees` — declare once on `Organization` |
| **OfferShippingDetails** | `shippingDestination` | `shippingRate`, `deliveryTime` |
| **ProfilePage** | `mainEntity` (Person/Organization) | `dateCreated`, `dateModified` |
| **DiscussionForumPosting** | `author`, `datePublished`, one of `text`/`image`/`video` | `headline`, `url`, `comment`, `interactionStatistic` |
| **Recipe** | `name`, `image` | `recipeIngredient`, `recipeInstructions`, `totalTime`, `nutrition`, `aggregateRating` |
| **JobPosting** | `title`, `description`, `datePosted`, `hiringOrganization`, one of `jobLocation`/`applicantLocationRequirements` | `validThrough`, `employmentType`, `baseSalary`, `directApply` |
| **SoftwareApplication** | `name`, `offers`, one of `aggregateRating`/`review` | `applicationCategory`, `operatingSystem` |
| **ImageObject** | `contentUrl` | `license`, `acquireLicensePage`, `creator`, `creditText` |

`Product` also needs **one of** `offers`, `review`, or `aggregateRating`. The value rules
(ISO dates, absolute URLs, numeric price, ISO 4217) and the `@id` graph conventions are
in `references/seo-schema/entity-graph.md`.

## Local & people types

| Type | Required | Recommended |
|---|---|---|
| **LocalBusiness** (and subtypes: Restaurant, Dentist, Plumber, …) | `name`, `address` (`PostalAddress`) | `telephone`, `geo`, `openingHoursSpecification`, `priceRange`, `url`, `image` |
| **PostalAddress** | `streetAddress`, `addressLocality`, `addressCountry` | `addressRegion`, `postalCode` |
| **Event** | `name`, `startDate`, `location` | `endDate`, `offers`, `performer`, `eventStatus`, `eventAttendanceMode` |
| **Person** | `name` | `jobTitle`, `worksFor`, `sameAs`, `url`, `image` |

## Cross-cutting validity rules

- **Match the visible page.** Marked-up values must reflect content a user can
  actually see; invented or hidden review/price/rating data is a violation.
- **Use the most specific type** that fits (e.g. `Dentist` over `LocalBusiness`)
  to inherit its expected properties.
- **One `@graph` per page** is the clean way to express multiple linked entities;
  share nodes via `@id` references instead of duplicating them.
- **Ratings need real aggregate data.** `AggregateRating` without a genuine
  `reviewCount` is invalid and risks a manual action.

## Retired rich-result displays (kept current)

FAQ rich results ended for **all** sites on May 7, 2026 (after an earlier narrowing
to government/health sites); HowTo rich results and the sitelinks search box are also
gone, as are the 2025-retired features (Course Info, Claim Review, Estimated Salary,
Learning Video, Special Announcement, Vehicle Listing). The markup stays valid and
machine-readable for ranking systems and AI answer engines, so the plugin still emits
it where genuinely useful but never promises the visual. The dated status table lives
in `search-landscape-2026.md` §5 — update that file, not this one, when Google changes
a feature.

## Free-path note

Generation and validation are fully offline and deterministic: the plugin builds
JSON-LD from supplied fields and checks required/recommended coverage against
this catalog without any external API. A connector (e.g. live rich-results
testing) only deepens the verdict; the offline structural check is the product.
