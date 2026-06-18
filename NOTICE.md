# NOTICE — Third-Party Material & Attributions

This plugin is **clean-room original**: every skill body, script, data file,
template, and reference document is authored from scratch for this plugin, and it
ships publicly on GitHub under the MIT License (see `LICENSE`). This file records
the few places where third-party material, standards, or externally defined
concepts are involved, and the terms under which they appear.

## Standards & specifications (referenced, not copied)

These are public technical standards. The plugin references and implements
against them; it does not redistribute their text.

- **WCAG 2.2** (W3C) — accessibility success criteria, referenced by the
  accessibility and QA skills.
- **Schema.org** vocabulary — structured-data types, referenced by the schema
  and SEO skills.
- **Core Web Vitals** (Google) — performance metric definitions.
- **IndexNow**, **Open Graph**, **robots.txt / sitemaps.org** — open web
  protocols, referenced by the technical-SEO skills.

## Externally named methodologies

Some skills originally referenced named methodologies from third parties. For a
clean-room, publicly-released plugin these have been handled as follows:

- **Evidence-led SEO loop** (formerly referenced as "FLOW") — the *idea* of an
  evidence-led find→leverage→optimize→win loop is not copyrightable, but the
  third-party name and its specific prompt set are. This plugin uses an
  **original methodology and original prompts** under its own naming. No
  third-party prompt text is included. See `references/PROVENANCE.md`.
- **Build-brief and design-brief frameworks** ("BLAST", "5 Core Dimensions") —
  retained as generic structural acronyms with **original section content**
  written for this plugin. If any third-party trademark concern is identified,
  rename per `references/PROVENANCE.md`.

## Optional external services (not bundled)

The plugin can *call* these when the user has installed/configured them
separately. None of their code, data, or credentials ship with this plugin:

- Playwright, Firecrawl, DataForSEO, nanobanana (Gemini image gen) MCP servers
- Google APIs (Search Console, PageSpeed Insights, CrUX, GA4)
- The `openai-codex` and `cc-gemini-plugin` cross-model tools

## Fonts & assets

Any font recommendations point to families under their own licenses (e.g. Google
Fonts under OFL/Apache). The plugin recommends fonts; it does not redistribute
font files.

---

If you believe any material here is improperly attributed, open an issue at
<https://github.com/ZachArticulateV/designer-pro-and-seo/issues> and it will be
corrected promptly.
