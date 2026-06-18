---
name: design-build
description: Generate distinctive, production-grade frontend UI code from a design system — starting from an on-brand, accessible, rendered HTML scaffold and elaborating with taste that avoids the generic-AI-slop aesthetic. Trigger when the user says "build the site", "make the UI", "design and code", "create a landing page", "build a component", or wants polished frontend that looks intentional rather than templated.
---

# design-build

**Family:** design
**Status:** Stable

## Purpose

The frontend code generator — and the payoff of the whole design loop. It takes a
design system (from `design-system-gen`) and **renders a real, on-brand starting
page** via `render_page.py` (semantic HTML5, the system's actual palette/type/
effects as CSS variables, `prefers-reduced-motion` fallback, `:focus-visible`
states, contrast-safe buttons), then elaborates it with taste. The differentiator
is the anti-slop discipline: distinctive type, color, and interaction instead of
the default gradient-purple, rounded-corner look — grounded in the chosen style's
characteristics from `data/ui-styles.csv`.

## Triggers

- "build the site" / "make the UI" / "design and code"
- "create a landing page" / "build a component"
- "make this beautiful" / "production-grade frontend"

## Inputs

- Design system (from `design-system-gen`, or "generate one")
- Page/component spec (from `blast-prompt`, or free-text)
- Stack (HTML+CSS+JS | React | Next.js | Vue | Svelte | Astro)
- Variants (1 = single build; 2+ = invokes `parallel-build`)

## Steps

1. **Get the design system.** Run `design-system-gen` if none exists; save JSON.
2. **Render the on-brand scaffold** — a real, accessible starting point, not a blank
   page:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/design/render_page.py" --design-json ds.json --out page.html
   ```
   (or `--product-type/--industry/--keywords` to run the engine inline).
3. **Elaborate with taste (anti-slop pass).** Replace placeholder copy (use
   `copywriting`), shape the sections to the brief, and add distinctive details that
   match the style's `characteristics` from `data/ui-styles.csv` — reject the
   generic AI look. Honor `data/ux-rules.csv` (one primary CTA, contrast, etc.).
4. **Target the stack.** For HTML+CSS+JS, build straight from the scaffold. For
   React/Vue/etc., translate the scaffold's structure + tokens into components
   (use `design-tokens-emit` for the token file).
5. **Variants.** If the user wants 2+, hand the brief + design system to
   `parallel-build`.
6. **Pre-delivery.** Run `design-accessibility` and `qa-gate` before handoff.

## Outputs

- Built files (HTML/CSS/JS or components), starting from a rendered on-brand scaffold
- A build manifest: tokens used, sections built, what was elaborated vs. scaffolded

## Dependencies

- `scripts/design/render_page.py` (required) — Python 3.10+, standard library only
- `design-system-gen` (tokens), `data/ui-styles.csv` + `data/ux-rules.csv` (taste
  constraints), `copywriting` (real copy), `design-tokens-emit` (component token
  files)

## Notes

The renderer guarantees a baseline that's already semantic, responsive, and
accessible — so the human/taste effort goes into distinctiveness, not boilerplate.
For internal tools, the user can request "default styling" mode to skip the
distinctiveness pass.

Related: for 2+ variants this skill hands the brief + tokens to `parallel-build`
(Step 5), which runs `design-build` per variant. That is a prose reference, not a
`Dependencies` edge, so the dependency graph stays acyclic.
