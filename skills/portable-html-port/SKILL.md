---
name: portable-html-port
description: Port a built site or page into a single-file portable HTML bundle that drops cleanly into any CMS or page builder with a "paste HTML" surface — WordPress (Elementor / Gutenberg / custom theme), GoHighLevel (Custom Code blocks), Webflow (custom code embed), Wix (HTML iframe), Framer (code embed), Squarespace, Carrd, or anything else. Trigger when the user says "port to wordpress", "put this in ghl", "single-file html", "make this embed-ready", "portable html", or needs to deliver a build inside an existing CMS rather than as a standalone Vercel/Netlify deploy.
---

# portable-html-port

**Family:** build-and-qa
**Status:** Stable

## Purpose

Convert a multi-file build (HTML + external CSS + external JS + local images) into
a single self-contained HTML file that pastes into any CMS/page-builder custom-HTML
surface with no per-platform tweaks. CSS and JS are inlined, small local images are
base64-embedded, large ones are flagged for CDN hosting, and dev artifacts
(source maps) are stripped.

## Triggers

- "port to wordpress" / "wp port"
- "put this in ghl" / "go high level" / "ghl port"
- "single-file html" / "portable html" / "make this embed-ready"
- "embed in webflow / wix / framer / squarespace"

## Inputs

- Source build entry file (the HTML to port) and its asset folder
- Target platform hint (wordpress / ghl / webflow / wix / framer / squarespace / carrd / generic)
- Inline-image size threshold (KB) — images larger stay external

## Steps

1. **Locate the entry HTML** and confirm its CSS/JS/images are local (remote
   `http(s)://` assets are left untouched on purpose).
2. **Run the porter** (try `python3`, then `py` on Windows):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/portable_html.py" \
     --in <path/to/index.html> --out <portable.html> \
     --target <platform> --inline-img-kb 50 --human
   ```
3. **Read the report.** It returns the output size, target-specific paste
   instructions, and warnings — including any images/JS left external and whether
   the file exceeds the target platform's inline-code limit.
4. **Handle warnings.** If the file exceeds a platform cap (e.g. Webflow ~50KB,
   GHL ~5MB/element) or large images were left external, recommend CDN-hosting
   those assets and re-run, or switch to a mixed strategy.
5. **Verify** the output renders standalone (open it / spot-check), then deliver it
   with the target-specific paste instructions from the report.

## Outputs

- `portable.html` — the single-file bundle
- A size + warnings report (JSON, or `--human` text) with paste instructions
- A list of any assets left external (to host on a CDN)

## Dependencies

- `scripts/workflow/portable_html.py` (required) — Python 3.10+, standard library only
- Optional: a browser (or Playwright) to verify the standalone render

## Notes

Platform quirks the output respects (the script encodes the size limits and paste
guidance per target):
- **WordPress** (Gutenberg Custom HTML block / Elementor HTML widget) — supports `<style>`+`<script>`
- **GoHighLevel** — Custom Code element; watch per-element size; CDN large media
- **Webflow** — custom-code embeds cap near 50KB; prefer external/CDN assets
- **Wix** — HTML iframe; isolated context, JS can't reach the parent page
- **Framer / Squarespace** — full HTML+CSS+JS embed support
- **Carrd** — Embed element (Code type); requires a Carrd Pro plan

A worked example lives in `references/examples/portable-html/`.
