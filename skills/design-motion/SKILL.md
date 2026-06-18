---
name: design-motion
description: Implement motion from a design system's motion tokens — emit real CSS/JS for entrance/scroll animations, micro-interactions (hover/press/focus), and transitions, with a reduced-motion fallback. Trigger when the user says "add motion", "animate this", "implement the animations", "micro-interactions", "scroll animations", "page transitions", or "make it feel alive".
---

# design-motion

**Family:** design
**Status:** Stable

## Purpose

The implementation counterpart to `design-dimensions` dimension 5. That skill
*specifies* motion; nothing *builds* it. This emits production-ready CSS (and
minimal JS where needed) from a design system's motion tokens — so "the brief said
250ms ease-out micro-interactions" becomes actual code, with an accessibility-safe
reduced-motion fallback every time.

## Triggers

- "add motion" / "animate this" / "make it feel alive"
- "implement the animations" / "micro-interactions"
- "scroll animations" / "page transitions"

## Inputs

- Motion tokens (duration, easing) — from a design system / `design-system-gen`
- The elements/sections to animate and the desired feel
- Stack (vanilla CSS/JS, Tailwind, React, etc.)

## Steps

1. **Read the motion tokens** — base duration + easing from the design system (e.g.
   `200ms ease-out`). If absent, propose sensible defaults and note it.
2. **Emit the reduced-motion guard first** — wrap motion so
   `@media (prefers-reduced-motion: reduce)` disables/*reduces* it. This is
   non-negotiable (accessibility).
3. **Generate the motion set** for the target stack:
   - **Entrance/scroll** — fade/slide-in on intersection (IntersectionObserver, or
     CSS scroll-driven animations where supported), respecting the token timing.
   - **Micro-interactions** — hover, press, and **focus-visible** states (focus
     parity matters for keyboard users).
   - **Transitions** — section/page transitions using the token easing.
4. **Keep it performant** — animate `transform`/`opacity` only; avoid layout-
   thrashing properties; no animation on the LCP element's first paint.
5. **Deliver code** ready to paste, plus a one-line note on where to place it.
   Offer to run `design-accessibility` to confirm reduced-motion behavior.

## Outputs

- Paste-ready CSS/JS (or framework equivalent) for the requested motion
- A required `prefers-reduced-motion` fallback block
- Performance notes (transform/opacity-only, LCP-safe)

## Dependencies

- None required (pure method). Composes with `design-dimensions` (spec source),
  `design-system-gen` (motion tokens), `design-accessibility` (reduced-motion check).

## Notes

Motion is the cheapest polish lever and the most-skipped — this skill makes
implementing it (and its reduced-motion fallback) routine. Always animate
`transform`/`opacity` for 60fps; never trap keyboard users by animating focus away.
