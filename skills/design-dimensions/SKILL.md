---
name: design-dimensions
description: Build a design prompt structured around the 5 Core Dimensions — Pattern & Layout (skeleton), Style & Aesthetic (skin), Color & Theme (palette), Typography (voice), and Motion & Interaction (life). Trigger when the user says "5 dimensions", "design prompt", "structured design brief", "the five-dimensions framework", or wants a design brief that covers all the load-bearing dimensions explicitly before a build.
---

# design-dimensions

**Family:** design
**Status:** Stable

## Purpose

A design-brief generator structured around the five dimensions that actually
determine whether a build looks intentional or generic. It forces all five to be
filled before the brief is "done" — especially Motion, the dimension that gets
skipped and that most cheaply separates a polished site from a flat one.

The five dimensions: **Pattern & Layout** (skeleton), **Style & Aesthetic**
(skin), **Color & Theme** (palette), **Typography** (voice), **Motion &
Interaction** (life).

## Triggers

- "5 dimensions" / "core dimensions"
- "design prompt" / "structured design brief"
- "five-dimensions framework"
- "give me a complete design prompt"

## Inputs

- Project context (or pull from a `design-research` result)
- An existing design system (or trigger `design-system-gen` first)
- The specific page/component the brief is for

## Steps

1. **Get a design system.** If one exists, use it. If not, run `design-system-gen`
   first — it supplies dimensions 1–4 (pattern, style, color, typography) directly.
2. **Load the template** `templates/dimensions-template.md` and fill dimensions
   1–4 from the design system (map palette hex, fonts/weights, pattern, style,
   effects into the matching slots).
3. **Fill dimension 5 (Motion) deliberately.** This is the one that gets skipped.
   Specify the base curve + duration, entrance/scroll behavior, micro-interactions
   (hover/press/focus), section transitions, and the **reduced-motion fallback**
   (required for accessibility).
4. **Run the completeness gate.** Every dimension must have substantive content —
   no "TBD", no empty Motion. Flag any gap and resolve it before proceeding.
5. **Render** the brief paste-ready. Offer to hand it to `design-build` or fold it
   into a full build brief via `blast-prompt`.

## Outputs

- Markdown brief with all five dimensions sectioned (from the template)
- Paste-ready version for a build agent
- A completeness gate confirming Motion (incl. reduced-motion) is specified

## Dependencies

- `templates/dimensions-template.md` (required)
- `design-system-gen` (typical upstream, supplies dimensions 1–4)

## Notes

Motion is the most-skipped dimension and the cheapest polish lever. This skill
exists partly to make Motion — and its reduced-motion fallback — non-optional.
