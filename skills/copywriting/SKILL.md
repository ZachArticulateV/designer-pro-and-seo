---
name: copywriting
description: Write conversion-focused copy for a page or section — headlines, subheads, value propositions, CTAs, feature/benefit blocks, and microcopy — anchored to a specific audience and offer. Trigger when the user says "write copy", "headline", "value proposition", "CTA copy", "hero copy", "rewrite this section", "make this convert", or needs words for a page rather than a design or audit.
---

# copywriting

**Family:** content-and-data
**Status:** Stable

## Purpose

Produce conversion copy that earns the click — the words a page needs, not a
critique of them. Fills the hole between `design-cro` (which reviews copy) and the
build (which needs copy to exist). Anchors every line to one audience and one
offer so it sounds specific, not generic.

## Triggers

- "write copy" / "hero copy" / "rewrite this section"
- "headline" / "subhead"
- "value proposition" / "CTA copy"
- "make this convert"

## Inputs

- Audience (who, and the problem they have) and the offer/product
- Page/section type (hero, features, pricing, CTA band, about)
- Desired tone (or pull from a design system / brand voice)
- Primary conversion action

## Steps

1. **Anchor.** State the one audience, their core pain, and the single desired
   action. All copy serves these three.
2. **Lead with outcome, not feature.** Draft the headline as the result the user
   gets; the subhead earns belief; the body proves it.
3. **Write the set** for the section type:
   - Hero: headline + subhead + primary CTA (+ optional risk-reducer microcopy).
   - Features: benefit-led blocks (benefit → how → proof), not feature lists.
   - CTA band: a verb-first button label + one friction-reducing line.
4. **Apply the rules:** one primary CTA, benefit before feature, concrete over
   vague, no jargon, headline readable in ~3 seconds, match search/ad intent.
5. **Offer 2–3 headline variants** at different angles (outcome / objection /
   curiosity) so the user can A/B later.
6. **Pass to** `design-cro` to pressure-test the result, or hand into a build brief
   (`blast-prompt` Blueprint section).

## Outputs

- Section-ready copy (headline, subhead, body, CTA, microcopy)
- 2–3 headline variants tagged by angle
- Notes on any claim that needs proof/substantiation before publishing

## Dependencies

- None required (pure method). Composes with `design-cro`, `blast-prompt`,
  `design-system-gen` (for tone).

## Notes

Truth-in-copy: don't write claims the client can't back up. Flag any
performance/outcome claim that needs a citation or disclaimer before it ships.
