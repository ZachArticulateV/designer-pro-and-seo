---
name: design-system-gen
description: Generate a complete design system (pattern, style, color palette, typography, effects, anti-patterns) from a product type, industry, and a few keywords. Trigger when the user says "design system", "pick colors / fonts for me", "generate a design system", "what style fits", "recommend a palette", or is starting a new build and needs a coherent visual language before writing code.
---

# design-system-gen

**Family:** design
**Status:** Stable

## Purpose

Produce a complete, opinionated design system in one pass. Given a product type,
target industry, and a handful of style keywords, return pattern & layout, style,
color palette (with WCAG contrast), typography pairing, effects (radius/shadow/
motion), explicit anti-patterns, and a pre-delivery checklist.

Backed by the local clean-room CSV libraries in `data/` and a deterministic
Python reasoning engine. No network or paid API required.

## Triggers

- "design system" / "generate a design system"
- "pick colors and fonts for me"
- "what style fits a [X] product"
- "recommend a palette for [industry]"
- "I'm starting a new build, give me the visual language"

## Inputs

- Product type (e.g. "saas-landing", "restaurant", "luxury-brand") — closest match from `data/product-types.csv`
- Industry / vertical
- Style keywords (free text — "modern, minimal, dark mode")
- Output: ASCII (`--human`) for the user, or JSON when a downstream skill consumes it

## Steps

1. **Gather inputs.** Ask for (or infer) product type, industry, and 2–5 style
   keywords. If the user is vague, suggest the nearest `product_type` from
   `data/product-types.csv`.
2. **Ensure the palette library exists.** If `data/color-palettes.csv` is missing,
   generate it first (idempotent, clean-room):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/design/gen_palettes.py"    # use `py` on Windows if python3 is absent
   ```
3. **Run the engine:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/design/design_system.py" \
     --product-type "<type>" --industry "<industry>" \
     --keywords "<comma,separated>" --human
   ```
   Drop `--human` (emit JSON) when handing the result to another skill.
4. **Read the result.** It returns pattern, style (+characteristics + what to
   avoid), palette (hex set + `text_on_bg_contrast` + `aa_body_text`), typography
   pairing (+weights + Google-Fonts availability), effects, key sections,
   anti-patterns, and the pre-delivery checklist. Note anything under `_fallbacks`.
5. **Sanity-check & adapt.** Confirm `aa_body_text` is `pass`. If keywords pulled
   an off-base style, re-run with refined keywords, or override one dimension and
   state why.
6. **Present & route.** Show the system, then offer to: persist it
   (`design-system-persist`), expand it into a brief (`design-dimensions` /
   `blast-prompt`), or emit code tokens (`design-tokens-emit`).

## Outputs

- Complete design system (ASCII summary or engine JSON)
- Pre-delivery checklist
- Named `_fallbacks` if any data library was missing

## Dependencies

- `scripts/design/design_system.py` (required) + the `data/*.csv` libraries
- `scripts/design/gen_palettes.py` (required once, to build the palette library)
- Python 3.10+ — standard library only, no third-party packages

## Notes

The most-invoked design skill; most other design skills call this first so all
variants share token consistency. The engine tolerates a partial data set and
flags which dimension fell back to a heuristic (see `references/ENGINE-CONTRACTS.md`).
