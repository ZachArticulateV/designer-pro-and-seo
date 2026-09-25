# seo-sitemap — Validation Codes, Quality Gates & Link Architecture

Durable knowledge behind `scripts/seo/sitemap_tools.py` and `scripts/seo/link_graph.py`.
Knowledge, not steps. Crawl facts (lastmod use, ignored changefreq/priority, IndexNow)
are dated in `references/shared/search-landscape-2026.md` §3.

## Why sitemaps and links are one job

A sitemap tells engines which URLs you *want* crawled. Internal links tell them which
URLs *matter* and how they relate. A page that appears in the sitemap but nothing
links to is an orphan. Google may crawl it, but it inherits no relevance and ranks
poorly. Audit both, and read them against each other.

## Validation codes (`--validate`)

| Code | Check | Severity |
|---|---|---|
| S01 | not well-formed XML | critical |
| S02 | over 50 MB uncompressed | critical |
| S03 | wrong namespace | high |
| S04 | empty set / unexpected root | critical |
| S05 | over 50,000 URLs (or child sitemaps) | critical |
| S06 | `<loc>` not absolute http(s) | critical |
| S07 | URLs on several hosts (www vs apex, other domains) | high |
| S08 | http and https mixed | high |
| S09 | duplicate `<loc>` | medium |
| S10 | `#fragment` URLs | medium |
| S11 | session / `utm_` tracking parameters | medium |
| S12 | lastmod not W3C datetime | medium |
| S13 | lastmod in the future (with `--as-of`) | medium |
| S14 | over 90% of 10+ URLs share one lastmod, the auto-bump tell | medium |
| S15 | no lastmod at all | info |
| S16 | changefreq / priority present (ignored by Google) | info |
| S20 | image:image without an absolute image:loc | high |
| S21 | video:video missing thumbnail / title / description / content-or-player loc | high |
| S22 | over 1,000 news entries | high |
| S23 | news:news missing publication name + language / date / title | high |
| S24 | news entries older than 2 days (with `--as-of`) | medium |
| S25 | hreflang `xhtml:link` href not absolute | high |
| S26 | hreflang self-reference or return link missing within the sitemap | high |

`valid` is false only for the protocol violations (S01, S02, S04, S05, S06). Hygiene
findings lower the score but leave a sitemap that engines will still read.

**lastmod discipline.** Generate lastmod from real per-URL change dates
(`--generate --lastmod-file url,date.csv`). One `--lastmod` stamped on every URL
triggers a warning. Once engines see lastmod move without content changing, they
stop trusting it for the whole site.

## Quality gates (`--crosscheck` / `--check-live`)

A sitemap should list only **200, indexable, self-canonical** URLs.

| Code | Gate | Severity |
|---|---|---|
| G1 | sitemap URL returns 4xx/5xx | high |
| G2 | sitemap URL redirects (status 3xx or a different final URL) | medium |
| G3 | sitemap URL is noindex (meta robots or X-Robots-Tag) | high |
| G4 | sitemap URL canonicalizes to another URL | high |
| G5 | a known indexable, self-canonical page is missing from the sitemap | medium |
| G0 | no page state supplied for a sitemap URL | info |

`--crosscheck` takes page states from any source: a crawler export, `tech_audit.py`
runs, or `--check-live`. `--check-live` fetches the first N URLs through the shared
SSRF guard and always states "fetched N of M". A full crawl is Tier-1.

## Link architecture (`link_graph.py`)

| Code | Finding | Severity | Why |
|---|---|---|---|
| L0 | home page missing from the set | high | depth can't be measured |
| L1 | orphan: no internal inbound link | high | no relevance flows in; discovery depends on the sitemap alone |
| L2 | unreachable from home (an island) | high | crawlers following links never arrive |
| L3 | broken internal target (complete `--dir` set) | high | wasted crawl + dead end for users |
| L4 | deeper than 3 clicks | medium | importance decays with depth; crawl frequency drops |
| L5 | dead end (no internal outlinks) | medium | no next step for users or crawlers |
| L6 | linked only from nav/header/footer | medium | template links carry little topical context |
| L7 | reached only via generic anchors | medium | the anchor is the strongest relevance hint a link carries |
| L8 | internal `rel=nofollow` | medium | nofollow is for untrusted links, not site structure |
| L9 | sitemap URL that is an orphan in the graph | medium | a sitemap entry is a hint, not a link |
| L10 | linked page missing from the sitemap | info | add it if canonical and indexable |

**Edges mode** (`--edges`, e.g. a crawler export) can't know whether an unlisted
target is really broken. There, L3 is downgraded to info and says so.

Click depth is computed over **all** internal links, navigation included, because
that is how crawlers walk. The contextual count (L6) excludes nav, header, footer and
aside, because that is where topical relevance comes from.

## Scoring

Both tools score `max(0, 100 − 25·critical − 10·high − 4·medium)` **per finding
type**, not per URL. A thousand orphans cost as much as one, and the `count` and
`urls` fields carry the scale. The goal is a triage ranking, not a punishment curve.

## Worked examples (pinned by `tests/test_sitemap_linkgraph.py`)

- **`sample-sitemap.xml` + `pages.json`** scores **82/100**:
  - G4: `/benches` canonicalizes to `/benches/classic` (−10)
  - G2: `/care-guide` 301s to `/guides/cedar-care` (−4)
  - G5: `/guides/cedar-care` is indexable but missing from the sitemap (−4)
- **`site/`**, a 9-page static build, scores **64/100**:
  - L1: the cedar-care guide is an orphan (−10)
  - L3: a porch-swing link is broken (−10)
  - L4: the finish and stain pages sit 4–5 clicks deep (−4)
  - L5: contact is a dead end (−4)
  - L6: about and contact are linked from nav/footer only (−4)
  - L7: the specs page is reached only by "Click here" (−4)
