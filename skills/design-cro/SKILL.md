---
name: design-cro
description: Run a heuristic conversion-rate-optimization review of a landing or funnel page — CTA hierarchy, above-fold weight, form friction, trust-signal placement, copy clarity, and decision fatigue — scoring each finding by impact over effort. Uses Playwright for in-browser thumb-zone and interaction checks when connected; otherwise reviews the fetched HTML and flags those as manual checks. Trigger when the user says "cro", "conversion review", "why isn't this converting", "landing page review", "funnel review", "improve conversions", or "checkout friction review".
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
- "checkout friction review"

## Inputs

- Target URL or local build path
- Conversion goal (lead form / signup / purchase / call)
- Target audience and page type (landing | pricing | checkout | signup | contact)

## Steps

1. **Run the CRO audit** on the URL (SSRF-guarded fetch) or local HTML:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/design/cro_audit.py" --file landing.html --goal lead --human   # or --url <URL>
   ```
   K1–K13 (`references/design-cro/cro-heuristics.md`): CTA presence and hierarchy in
   the first screen, generic CTA labels, form length and needlessly required fields,
   trust signals and their distance from the decision, contact path and tap-to-call,
   headline clarity, first-screen value copy, autoplay media, long pages with one CTA.
   Each finding cites its `data/ux-rules.csv` conversion rule and carries Impact +
   Effort.
2. **Judge what the script can't** — visual weight and contrast of the primary CTA,
   whether the offer itself is compelling, message match with the ad / search intent.
3. **Optional in-browser pass.** If Playwright is available, check thumb-zone
   reachability and real interaction; otherwise note that as a manual check.
4. **Score each finding** by Impact (high/med/low) and Fix Effort (high/med/low).
5. **Render** the findings ordered by Impact ÷ Effort, each with a specific fix.
   For copy fixes, hand to `copywriting`.

## Outputs

- CRO report: prioritized fix list, each tagged Impact + Effort, ordered by leverage
- Specific, actionable recommendation per finding

## Dependencies

- `scripts/design/cro_audit.py` (required) — the K1–K13 heuristic engine
- `data/ux-rules.csv` (required) — the conversion rule set each finding cites
- `references/design-cro/cro-heuristics.md` (required) — catalog, leverage ranking, limits
- Playwright (optional — adds in-browser thumb-zone/interaction checks; free path: manual thumb-zone inspection of the fetched HTML, noted in the report)
- `copywriting` (optional — drafts copy fixes; free path: inline copy recommendation per finding)

## Notes

CRO heuristics produce *hypotheses to test*, ranked by likely impact — not a
substitute for A/B testing. Pair with `seo-drift` to confirm changes caused no SEO
regression.
