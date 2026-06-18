---
name: design-tokens-emit
description: Convert a design system spec into code-deliverable token files — CSS variables, a Tailwind config fragment, SCSS variables, or Style-Dictionary JSON. Trigger when the user says "emit tokens", "tailwind config", "css variables", "style dictionary", "convert design system to code", or wants to bridge from spec to implementation.
---

# design-tokens-emit

**Family:** design
**Status:** Stable

## Purpose

Bridge "we have a design system spec" to "we have tokens we can `import`." Takes a
`design-system-gen` result and emits real token files in the chosen format(s), so
the palette/typography/effects become part of the build instead of staying a doc.

## Triggers

- "emit tokens" / "convert design system to code"
- "tailwind config" / "css variables" / "style dictionary"
- "tokens for [tailwind/css/scss]"

## Inputs

- A design system as **engine JSON** from `design-system-gen` (re-run it in JSON
  mode if you only have a saved `MASTER.md` — the emitter reads JSON, not Markdown)
- Target format: `css` | `tailwind` | `scss` | `json` | `all`
- Output directory

## Steps

1. **Get the design JSON.** Run `design-system-gen` (JSON mode) or read a saved one.
2. **Emit tokens:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/design/tokens_emit.py" --design-json ds.json --format all --out-dir tokens/
   ```
   Produces `tokens.css` (`:root` custom properties), `tailwind.tokens.js` (merge
   into `theme.extend`), `_tokens.scss`, and `tokens.json` (Style-Dictionary shape).
   Use `--print` to preview without writing.
3. **Wire it in.** Tell the user where each file goes (import the CSS, merge the
   Tailwind fragment, `@use` the SCSS) and include the contrast-safe `on_primary`
   color for button text.
4. **Keep it in sync.** Re-run when the design system changes; tokens are generated,
   not hand-maintained.

## Outputs

- One token file per requested format (CSS / Tailwind / SCSS / JSON)
- Wiring notes for the target stack

## Dependencies

- `scripts/design/tokens_emit.py` (required) — Python 3.10+, standard library only
- `design-system-gen` (upstream source of the tokens)

## Notes

Pairs with `design-build` (which consumes the tokens) and `design-system-persist`
(which stores the source design system). SwiftUI/Compose targets are on the roadmap;
web formats ship today.
