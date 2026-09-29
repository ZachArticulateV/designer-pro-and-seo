# seo-technical — Check Catalog, Severity Rationale & Lab Score

The durable knowledge behind `scripts/seo/tech_audit.py`: what every check looks for,
why it carries its severity, and how the lab score is computed. Knowledge, not steps.
The steps live in `skills/seo-technical/SKILL.md`. Dated facts (the 2 MB limit, retired
rich results, crawler classes) are sourced from `references/shared/search-landscape-2026.md`.

## Severity ladder

| Severity | Meaning | Lab-score penalty |
|---|---|---|
| **critical** | The page cannot rank, or is invisible to a whole class of engine | −25 |
| **high** | Ranking, rich-result or AI-citation eligibility is materially impaired | −10 |
| **medium** | A real defect with a bounded, usually incremental cost | −4 |
| **info** | Observed state, a pass, or an optional improvement | 0 |

**Lab score** = `max(0, 100 − Σ penalties)` over the findings actually observed.
It is deterministic and never includes a synthesized field number: field Core Web
Vitals stay in `needs_tier1` until `seo-google` supplies CrUX/PSI data. A skipped
check (no URL, so no headers or robots) simply adds no penalty. It is never scored
as a failure.

## The ten dimensions

### crawlability
- **AI-crawler policy** from the shared RFC 9309 evaluator (`ai_crawlers.py`).
  A blocked Googlebot/Bingbot is **critical**, because it also removes AI Overviews,
  AI Mode and Copilot visibility. Blocking every AI-search crawler is **high**, a
  partial block is **medium**, and blocking training bots only is **info** (a
  legitimate choice).
- **No `Sitemap:` directive** is **medium**, since discovery then leans on links alone.
- **More than one redirect hop** before the page is **medium**. Every hop costs crawl
  budget and latency, so link straight to the final URL.

### indexability
- **noindex** (meta robots, `googlebot` meta, *or* the `X-Robots-Tag` header) is
  **critical**. The header is easy to miss because it never shows in view-source.
- **noindex plus rel=canonical** is **high**. They are contradictory instructions,
  so pick one.
- **nosnippet / max-snippet:0** is **medium**. It suppresses the snippet *and*
  eligibility for AI Overview / AI Mode use. It is flagged so the choice is deliberate.
- **Canonical:** missing is **medium**. Several *different* canonicals is **high**,
  because engines ignore conflicting hints. Relative is **medium**. Cross-host is
  **medium** (fine for syndication, but confirm it).
- **HTML over 2 MB uncompressed** is **critical**, because Googlebot indexes only the
  first 2 MB. Over 1 MB is **medium** as an early warning, since hydration JSON and
  inline SVG usually cause the bloat.
- **No doctype** (quirks mode), **no charset**, and **no `<html lang>`** are each
  **medium**.
- **hreflang present** is **info**, with an x-default note. Full cluster validation
  (reciprocity, codes) belongs to `seo-hreflang`.

### security
- **Not HTTPS** is **critical**.
- **True mixed content** is **high**: an `http://` *sub-resource* (img, script,
  stylesheet link, iframe, source, video, audio, embed) on an https page. A plain
  `<a href="http://…">` is **not** mixed content, only a wasted redirect hop, so it is
  **info**.
- **Missing HSTS / CSP / X-Content-Type-Options / Referrer-Policy** is **medium**
  (only when fetched).

### url-structure (only when a URL is supplied)
- A **session id in the query** is **high** (infinite duplicate URLs).
- **Uppercase in the path** or **more than 2 query parameters** is **medium**.
  Over **115 characters** is **medium**.
- **Underscores** are **info**. Prefer hyphens for new URLs, but never redirect
  working URLs just for this.

### mobile
- **No viewport meta** is **high** (mobile-first indexing is complete).
- **Zoom disabled** (`user-scalable=no`, `maximum-scale` under 2) is **medium**.
  It is an accessibility failure (WCAG 1.4.4) on the agent Google indexes with.

### cwv (lab heuristics, always labeled "lab")
- **First content image `loading=lazy`** is **high**, because it is usually the LCP
  element and lazy-loading delays it.
- **Render-blocking `<script src>` in `<head>`** (no `async`/`defer`, not a module)
  is **medium** and delays first render and LCP.
- **`<img>` without width+height and without CSS `aspect-ratio`** is **medium**, a
  direct CLS cause.
- **Inline script or JSON over 100 KB** is **medium**. It adds parse and hydration
  cost (INP) and index-size risk.
- **No image with `fetchpriority=high`** is **info**.

These are *risk signals*, not measurements. A page can pass all of them and still fail
field CWV.

### structured-data
- **No JSON-LD** is **high**. Hand off to `seo-schema`.
- **A block that doesn't parse** is **high**, because one syntax error drops the whole
  block.
- **Retired rich-result types present** (per `schema_gen.SPEC`, e.g. FAQPage, HowTo)
  are **info**. Keep the markup, but expect no visual.

### js-rendering
- **Client-rendered shell** is **high** when either a known app root (`#root`,
  `#app`, `#__next`, …) holds under 60 words of server HTML, or the page has JS and
  fewer than 20 words in total. AI-search crawlers and most assistants don't run
  JavaScript. A short but fully server-rendered page is *not* flagged.
- **`<a>` without a crawlable href** (missing, or `javascript:`) is **medium**.
  Crawlers follow hrefs, not onclick handlers.

### serp-presentation
- **Missing title** is **critical**. **Several titles** is **high**. **Over 60
  characters** or **under 15** is **medium**.
- **Missing meta description** is **high**. **Outside 50–165 characters** is **medium**.
- **No `<h1>`** is **high**. **Several** is **medium**.
- **Open Graph incomplete** (title, description or image) is **medium**. Share
  previews and some AI surfaces read OG.
- **Images missing `alt`** is **medium**, with detail handed to `seo-image-audit`.

### indexnow
Guidance only. IndexNow notifies Bing, Yandex, Seznam, Naver and other participating
engines, but not Google. It can't be observed from one page, so it never scores.

## Worked example

`references/examples/seo-technical/sample-page.html` scores **64/100**:

- 2 high findings × 10: mixed-content badge image, lazy-loaded hero
- 4 medium findings × 4: missing og:image, one render-blocking head script, one image
  without dimensions, one image without alt

That gives 100 − 20 − 16 = 64. Every point traces to a finding with a fix.
