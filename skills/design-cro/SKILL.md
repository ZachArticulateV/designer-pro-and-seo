---
name: design-cro
description: Run a heuristic conversion-rate-optimization review on a landing page or funnel — CTA hierarchy, form friction, trust signals, copy clarity, above-fold weight, decision fatigue. Trigger when the user says "cro", "conversion review", "why isn't this converting", "landing page review", "funnel review", "improve conversions", or before/after a landing-page launch.
---

# design-cro

**Family:** design
**Status:** Stable

## Purpose

A dedicated CRO skill. Runs a heuristic review of a landing page or funnel against
established conversion principles and produces a prioritized list of
conversion-killing issues with specific fixes. Works on a URL or local HTML with no
external tools; Playwright optionally adds in-browser checks (thumb zones, real
interaction).

Reviews against: CTA hierarchy (one primary), above-fold weight, form friction,
trust signals near the decision, copy clarity (benefit-led, 3-second headline),
decision fatigue, and mobile reality.

## Triggers

- "cro" / "conversion review" / "improve conversions"
- "why isn't this converting"
- "landing page review" / "funnel review"

## Inputs

- Target URL or local build path
- Conversion goal (lead form / signup / purchase / call)
- Target audience and page type (landing | pricing | checkout | signup | contact)

## Steps

1. **Get the page.** Fetch the URL or read the local HTML (this is the free path).
2. **Walk the heuristic checklist**, cross-referencing `data/ux-rules.csv` (the
   `conversion` and `cta` tagged rules): is there exactly one primary CTA? Is the
   value prop above the fold? How many form fields? Are trust signals near the CTA?
   Does the headline read in ~3 seconds? Any decision fatigue / competing actions?
3. **Optional in-browser pass.** If Playwright is available, check thumb-zone
   reachability and real interaction; otherwise note that as a manual check.
4. **Score each finding** by Impact (high/med/low) and Fix Effort (high/med/low).
5. **Render** the findings ordered by Impact ÷ Effort, each with a specific fix.
   For copy fixes, hand to `copywriting`.

## Outputs

- CRO report: prioritized fix list, each tagged Impact + Effort, ordered by leverage
- Specific, actionable recommendation per finding

## Dependencies

- None required (heuristic review of provided HTML/URL); `data/ux-rules.csv` for the
  conversion/CTA rule set
- Optional: Playwright (in-browser thumb-zone/interaction); `copywriting` (copy fixes)

## Notes

CRO heuristics produce *hypotheses to test*, ranked by likely impact — not a
substitute for A/B testing. Pair with `seo-drift` to confirm changes caused no SEO
regression.
