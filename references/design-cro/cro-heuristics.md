# design-cro — Heuristic Catalog, Leverage Ranking & Limits

The durable knowledge behind `scripts/design/cro_audit.py`. Knowledge, not steps. The
rules it enforces are the `conversion`-category rows of `data/ux-rules.csv`, and each
finding cites its row, so the design data and the engine stay one source.

## The model: friction vs. motivation at the decision point

A visitor converts when motivation outweighs friction at the moment of decision. Every
heuristic below either:
- **raises motivation**: a clear outcome headline, a value proposition, proof near the
  decision; or
- **removes friction**: one obvious action, short forms, tap-to-call, no competing exits.

## Catalog

| Code | Heuristic | Impact / effort | ux-rules.csv row |
|---|---|---|---|
| K1 | no CTA on the page | high / low | One primary CTA per view |
| K2 | no CTA in the first screen | high / low | One primary CTA per view |
| K3 | more than 2 distinct CTA labels in the first screen | med / low | One primary CTA per view |
| K4 | generic CTA label (Submit, Learn more, Click here…) | med / low | — |
| K5 | form over 5 visible fields (over 8 = high impact) | med–high / med | Minimize required form fields |
| K6 | phone / company / address marked required | med / low | Minimize required form fields |
| K7 | no trust signals at all | high / med | Trust signals near conversion points |
| K8 | trust signals exist but not within about 1,500 characters of a form or button | med / low | Trust signals near conversion points |
| K9 | no contact path, or a phone number that isn't a `tel:` link | med (high for a call goal) / low | — |
| K10 | no H1, a generic "Welcome…" H1, or an H1 over 12 words | high–med / low | Page reflects intent in first 3 seconds |
| K11 | fewer than 8 words of value copy in the first screen (CTA text excluded) | med / low | Value proposition visible without scrolling |
| K12 | autoplay video without muted + controls | med / low | — |
| K13 | page over 1,200 words with a single CTA and no sticky CTA | med / low | Sticky CTA on long mobile pages |

**"First screen"** is the content before the first `<h2>`. When a page has no `<h2>`,
it is the first 20% of the main content, and never less than about 1,500 characters.
Header, nav and footer are excluded, so menu links never count as CTAs.

**Trust signals** are words and markup such as reviews, ratings, stars, guarantees,
warranties, certifications, licenses, awards, "as seen in", years in business, case
studies, insurance, or `Review` / `aggregateRating` markup. On YMYL pages (health,
finance, legal), pair this with the content audit's credential checks.

## Leverage ranking

Findings are ordered by **impact ÷ effort** (high 3, med 2, low 1). A high-impact,
low-effort fix such as a generic headline goes first, and a form rebuild goes later.
The score (`100 − 10·high − 4·medium`) is for tracking between releases, not a
conversion forecast.

## What this can't tell you

These are hypotheses, not results. The engine can't see:
- visual weight
- color contrast of the CTA
- thumb reach on a real phone
- load speed on a mid-range device
- whether the offer itself is compelling

It lists the first two physical checks under `manual_checks`. Playwright plus
`design-visual-qa` deepen them. Validate the top three findings with an A/B test or a
before/after conversion comparison, and run `seo-drift` so a CRO change doesn't break SEO.

## Worked example (pinned by `tests/test_design_qa.py`)

`references/examples/design-cro/landing.html` scores **60/100** with this leverage
order:
1. K10: "Welcome to Cedar Bench Co." headline
2. K3: four competing hero CTAs
3. K4: "Learn more" / "Submit"
4. K6: phone and company required
5. K9: the phone number isn't tap-to-call
6. K11: no value copy in the first screen
7. K5: a 9-field quote form
