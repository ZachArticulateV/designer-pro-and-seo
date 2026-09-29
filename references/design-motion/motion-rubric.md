# design-motion — Motion Rubric: Accessibility, Performance, Tokens

The durable knowledge behind `scripts/design/motion_audit.py`, and the rules
`design-motion` generates code against. Knowledge, not steps.

## Three non-negotiables

1. **Reduced motion is honored.** Users who set `prefers-reduced-motion: reduce` get
   near-zero motion. This matters to people with vestibular disorders, and it is
   WCAG 2.3.3 at AAA. Anything that moves for more than 5 s also needs a pause or stop
   (WCAG 2.2.2, AA). The guard ships with the first animation, not after it.
2. **Only composited properties move.** Animate `transform` and `opacity`. Animating
   `width`, `height`, `top`, `left`, margins or padding forces layout on every frame.
   That costs jank, CLS when content shifts, and INP when it collides with input.
3. **Focus stays visible.** Motion work often "cleans up" focus rings. Never remove an
   outline without a `:focus-visible` replacement (WCAG 2.4.7), with a ring of at least
   3:1 contrast.

## Audit codes

| Code | Check | Severity |
|---|---|---|
| M1 | animated rules with no `prefers-reduced-motion` query | high |
| M2 | transitions or keyframes on layout properties | medium |
| M3 | `transition: all` (animates whatever changes, including layout) | medium |
| M4 | UI motion over 1000 ms (over 500 ms = info) | medium |
| M5 | infinite animation not stopped under reduced motion | medium |
| M6 | autoplaying or looping video without muted + controls | medium |
| M7 | `scroll-behavior: smooth` not reset under reduced motion | info |
| M8 | `outline: none/0` on `:focus` with no visible `:focus-visible` style | high |
| M9 | more than 6 distinct durations: timing isn't tokenized | info |

A reduced-motion block "stops" motion when it sets animation or transition to `none`,
or to a near-zero duration (`0`, `.01ms`), or pauses animation. It can do this globally
(`*`, `html`, `body`, `:root`) or for the same selector.

## The guard to ship

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Use `.01ms`, not `0`, so `animationend` / `transitionend` listeners still fire.

## Timing tokens

| Token | Duration | Use |
|---|---|---|
| `--dur-fast` | 120–150 ms | hover, press, toggles |
| `--dur-base` | 200–250 ms | menus, popovers, small enters/exits |
| `--dur-slow` | 350–400 ms | drawers, page-level transitions |

Ease-out (`cubic-bezier(.2,.8,.2,1)`) for entrances, ease-in for exits. Anything over
500 ms needs a reason: it is usually decoration competing with the content.
`design-system-gen` emits these tokens, and `design-tokens-emit` writes them as CSS
variables.

## Limits

The audit reads CSS statically. Motion driven from JavaScript (GSAP, Framer Motion,
IntersectionObserver class toggles, Web Animations API) must check
`matchMedia('(prefers-reduced-motion: reduce)')` itself. Verify that by hand or with
Playwright plus `design-accessibility`.

## Worked example (pinned by `tests/test_design_qa.py`)

`references/examples/design-motion/` scores **60/100**:

- **2 high:**
  - M1: five animated rules, no guard
  - M8: `.btn:focus { outline: none }`
- **5 medium:**
  - M2: `height`, `max-height` and `@keyframes slide-in` on `left`
  - M3: `transition: all` on `.card`
  - M4: a 1200 ms accordion
  - M5: an infinite pulse
  - M6: an autoplay loop without controls
- **Info:** M7, smooth scrolling.
