# seo-hreflang — Code Rules, Cluster Checks & Scoring

The durable knowledge behind `scripts/seo/hreflang_tools.py`. Knowledge, not steps.
hreflang also appears in sitemaps (checked by `sitemap_tools.py` codes S25/S26) and in
the technical audit (presence only, `tech_audit.py`).

## What hreflang is for

hreflang tells engines which URL to show a searcher based on language (and optionally
region). It is a **cluster-level** annotation. Every member must list every member,
including itself, and every link must be returned. An unreturned pair is ignored. A
page that fails validation doesn't just lose its own annotation; it can drop the
whole pair.

## Code rules

- **Language**: ISO 639-1, two letters (`en`, `fr`, `zh`, `se` = Northern Sami).
  Three-letter or invented codes are invalid. Common mistakes with a suggested fix:
  `jp`→`ja`, `cn`→`zh`, `dk`→`da`, `gr`→`el`, `cz`→`cs`, `ua`→`uk`, `vn`→`vi`,
  `iw`→`he`, `in`→`id`.
- **Region** (optional): ISO 3166-1 alpha-2 (`US`, `GB`, `BR`). `UK` is not a country
  code (use `GB`). `EU`, `LA` and numeric UN M.49 regions (`es-419`) are not
  supported. Target countries individually, or use the language alone.
- **Script** (optional): ISO 15924 between language and region, e.g. `zh-Hant-TW`,
  `sr-Latn`.
- **`x-default`**: the fallback for users who match no listed locale. It is usually a
  language picker or the primary site. One target, the same on every page.

## Cluster checks (`--cluster`)

| Code | Check | Severity |
|---|---|---|
| H1 | page has no hreflang at all | high |
| H2 | invalid language / region / script code | high |
| H3 | no self-reference with a language code (`x-default` pointing at itself does not count) | high |
| H4 | no x-default | medium |
| H5 | non-absolute href | high |
| H6 | alternate not in the audited set (can't verify its return link) | info |
| H7 | no return link: B doesn't point back to A (x-default excluded) | high |
| H8 | one URL carries different codes on different pages | medium |
| H9 | the page's own code disagrees with `<html lang>` | medium |
| H10 | an alternate is noindex | high |
| H11 | an alternate canonicalizes elsewhere (never canonicalize across locales) | high |
| H12 | different x-default targets across the cluster | medium |

Findings reported from both sides of a pair are deduplicated. Pass the pages as a
manifest `{url: file}`, or as HTML files whose canonical gives their URL.

## Delivery methods

HTML `<link>` tags in `<head>`, the `Link:` HTTP header (for PDFs and non-HTML), or
`xhtml:link` in the sitemap. Choose **one** method per cluster. Mixed methods are
legal but multiply the places a mismatch can hide. `--generate` emits the tag set for
every page.

## Scoring

`max(0, 100 − 25·critical − 10·high − 4·medium)` per finding type.

## Worked example (pinned by `tests/test_hreflang_commerce.py`)

`references/examples/seo-hreflang/` is an en / fr / de cluster. It scores **68/100**:

- **2 high (−20):**
  - H7: `/de/` doesn't return the `/fr/` link
  - H2: `en-uk`
- **3 medium (−12):**
  - H4: `/fr/` has no x-default
  - H9: `/de/` declares `de-de` but `<html lang="en">`
  - H12: the x-default points at `/` on one page and `/de/` on another
- **Info:** H6, `/uk/` is outside the audited set.
