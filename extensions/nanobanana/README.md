# Extension: image generation (Gemini "Nano Banana")

**Enables:** AI image generation — OG/social preview images, blog hero images,
product shots, infographics, favicons — with SEO-aware presets.

**Used by:** `seo-image-gen` (the generation half; `seo-image-audit` is the
audit half and needs none of this).

There is **no official Google image-generation MCP**. This plugin's image-gen
skill is therefore *tool-aware* (see `references/CAPABILITY-TIERS.md`) and routes
to whatever you have, in this order:

1. **Recommended — Gemini CLI (Tier 3).** If `gemini` is on your PATH, the skill
   uses it directly to generate images. Install: `npm i -g @google/gemini-cli`
   (verified on npm), then authenticate per Google's docs. Check availability with
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/capability_probe.py"` (`cli.gemini`).
2. **Provider API key (Tier 1).** If you set an image-provider key (e.g.
   `GEMINI_API_KEY`) and run a Gemini-image MCP, the skill will use it.
3. **None available (Tier 4).** The skill outputs ready-to-use prompts + correct
   dimensions/naming so you can generate elsewhere, and tells you how to enable a
   higher tier.

## Optional: a community image-gen MCP

The bundled `.mcp.json` pins **`nano-banana-mcp@1.0.3`** purely as a *working
example*. It is a **community package, not official and not vetted by this
project** — review its source and permissions before installing, or swap `args`
for any Gemini-image MCP you trust. The recommended path above (Gemini CLI) needs
no third-party MCP at all.

To use it: set `GEMINI_API_KEY`, merge `.mcp.json`, and verify the tools appear.

## Note on generated assets

You are responsible for the rights to use generated images commercially; review
the image model's terms. Generated files go to your project workspace.
