---
name: seo-image-gen
description: Generate SEO-ready images (OG/social preview, blog hero, product, infographic, favicon) at correct dimensions with SEO-aware naming and alt text WHEN an image generator is available — the Gemini CLI or an image MCP/provider key; otherwise deliver production-ready prompts + exact specs to generate elsewhere (there is no built-in renderer, so the default with no generator is prompts+specs, not images). Trigger when the user says "generate image", "og image", "social preview", "hero image", "product photo", "infographic", "favicon", or "create a visual".
---

# seo-image-gen

**Family:** seo
**Status:** Stable

## Purpose

The generation half of image SEO (split from the audit because it carries different
legal/asset/API risk). Produces images at correct dimensions with SEO-aware presets,
file naming, and suggested alt text. It is **tool-aware**: it renders through
whatever generator you have — preferring the Gemini CLI — and, when no generator is
available, still delivers production-ready prompts + exact specs + filenames + alt
text so you can generate elsewhere. That prompts-and-specs output is real value on
its own; it never just fails.

## Triggers

- "generate image" / "create a visual"
- "og image" / "social preview"
- "hero image" / "blog image"
- "product photo" / "infographic" / "favicon"

## Inputs

- Subject/prompt and brand context (palette, style — pull from a design system)
- Preset: og | hero | product | infographic | favicon
- Output path (in the user's project workspace)

## Steps

1. **Pick the preset** and resolve its spec — e.g. OG 1200×630; hero ~1600×900;
   favicon set (16/32/180/512). Pull palette/style from a `design-system-gen` result
   so generated images match the brand.
2. **Compose the generation prompt** — subject + style + palette + composition, with
   negative prompts to avoid unwanted text artifacts.
3. **Detect generators.** Run `scripts/workflow/capability_probe.py` and check for a
   connected image-gen MCP. Route per the cascade below.
4. **Generate or hand off.** If a generator is available, render at the preset
   dimensions into the user's workspace. If none is, output the prompt + exact specs
   and stop with a one-line note on how to enable rendering (install the Gemini CLI
   or connect an image-gen MCP/provider key).
5. **Name + alt.** SEO-friendly filename (kebab-case, descriptive) + suggested alt
   text per image.
6. **Hand to** `seo-image-audit` to verify generated assets pass the audit.

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`). For image generation there is no built-in Claude
renderer, so the numbers run 3 → 1 → 4 by design (the CLI is preferred over an MCP):

1. **Tier 3 — Gemini CLI (preferred).** If `gemini` is on PATH (per
   `capability_probe.py`), use it to render at the preset dimensions.
2. **Tier 1 — image-gen MCP / provider key.** Otherwise, if an image-gen MCP is
   connected or a provider key is set (see `extensions/nanobanana/`), render with it.
3. **Tier 4 — guided (always available).** If neither is present, deliver the
   production-ready prompts + exact specs + filenames + alt text, and offer the
   options to enable rendering (install `@google/gemini-cli`, or connect an image MCP).

Always state which tier ran and how to enable rendering if it didn't.

## Outputs

- Generated image(s) at preset dimensions (Tier 3 or Tier 1)
- Otherwise: ready-to-use prompts + exact specs + SEO filenames + suggested alt text
- A one-line "to render here, install/connect …" note when handing off

## Dependencies

- Optional generator (one of): the Gemini CLI (`@google/gemini-cli`, preferred), or
  an image-gen MCP / provider key (`extensions/nanobanana/`). Required only to
  actually render; the prompts+specs path works without any.
- `design-system-gen` (optional — for brand-matched output)
- `scripts/workflow/capability_probe.py`

## Notes

You are responsible for the commercial rights to generated images; review the
model's terms (see `extensions/nanobanana/README.md`). Pairs with `seo-image-audit`.
