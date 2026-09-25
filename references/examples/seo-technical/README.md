# Golden example — seo-technical (Tier-2: `tech_audit.py`)

Proves the **free, key-absent Tier-2** path of `seo-technical` produces a real
9-category technical audit with no network and no API key — the `cwv-field`
capability's built-in product. Reproducible offline.

## Input

- `sample-page.html` — a small static page (fictional brand) seeded with real,
  fixable technical defects: a lazy-loaded hero image (the likely LCP element), a
  render-blocking head script, an `http://` badge image on an https page (true mixed
  content), an image without dimensions (CLS), an image without `alt`, and an Open
  Graph set missing `og:image`. It also has a plain `http://` *link*, which is correctly
  reported as info, not mixed content. Title, meta, canonical, viewport, lang and
  JSON-LD are healthy.

## Command

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/tech_audit.py" \
  --file references/examples/seo-technical/sample-page.html \
  --url https://example.test/benches --no-network --human
```

(From the repo root during development, drop `${CLAUDE_PLUGIN_ROOT}/` and run the
bare `scripts/...` path.)

## Expected free deliverable (Tier 2)

Header: `lab score 64/100`. Then findings by severity, each with a `fix:` line:

- `[HIGH] (security) Mixed content: http:// resources on the page`
- `[HIGH] (cwv) First (likely LCP) image is loading=lazy (lab)`
- `[MEDIUM] (serp-presentation) Open Graph incomplete: missing og:image`
- `[MEDIUM] (cwv) 1 render-blocking <script> in <head> (lab)`
- `[MEDIUM] (cwv) 1/3 <img> without width/height (CLS risk, lab)`
- `[MEDIUM] (serp-presentation) 1/3 <img> missing alt (use seo-image-audit)`
- `[INFO]` lines confirming title, meta description, single `<h1>`, canonical, lang,
  viewport, one Product JSON-LD block, and the plain `http://` link.
- A `[CWV]` line with the LCP<2.5s / CLS<0.1 / INP<200ms targets, noting that
  synthetic tools can't measure *field* CWV.

The score is 100 − 2×10 − 4×4 = 64 (formula in
`references/seo-technical/check-catalog.md`); `tests/test_tech_audit.py` pins it.

No field-CWV number is fabricated. `needs_tier1` (field CWV via CrUX/PSI, real
Lighthouse score) is satisfied only by adding a free Google key via `seo-google`
(Tier 1). The audit above is complete on its own — the product.
