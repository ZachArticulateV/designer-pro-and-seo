# NOTICE — Third-Party Material & Attributions

This plugin is **clean-room original**: every skill body, script, data file,
template, and reference document is authored from scratch for this plugin, and it
ships publicly on GitHub under the MIT License (see `LICENSE`). This file records
the few places where third-party material, standards, or externally defined
concepts are involved, and the terms under which they appear.

## Acknowledgements & inspiration

The vision and many of the ideas behind this plugin were sparked by the **AI
Automations by Jack** Skool community — sincere thanks to Jack and everyone there.
Those ideas inspired the approach; the plugin's code, content, and data are authored
independently for this plugin, and no community material is bundled or redistributed.

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
- **RFC 9309** (Robots Exclusion Protocol, IETF) — the robots.txt matching rules
  `scripts/seo/ai_crawlers.py` implements.
- **ISO 639-1 / ISO 3166-1 / ISO 15924 / ISO 4217** — language, region, script and
  currency codes checked by the hreflang and schema engines. Code lists are used as
  data; no standard text is reproduced.
- **Google image / video / news sitemap extensions** and **hreflang** annotations —
  public element names validated by the sitemap and hreflang engines.
- **llms.txt** — a public community proposal for a Markdown site summary; the format is
  implemented from its published description (`scripts/seo/llms_txt.py`).
- **AI crawler user-agent tokens** (GPTBot, OAI-SearchBot, ClaudeBot, Claude-SearchBot,
  PerplexityBot, Google-Extended, …) — operators' publicly documented names, used only
  to read and write robots.txt rules. Product names belong to their owners.

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

## Common Crawl (open web-graph data, queried not redistributed)

Some optional free-path features (e.g. host-level backlink and authority-proxy
discovery) can query the **Common Crawl** public web-graph and index, an openly
available dataset published by the Common Crawl Foundation. The plugin reads
Common Crawl data over the network at the user's request and derives its own
metrics from it; it **does not bundle, mirror, or redistribute** any Common Crawl
files. Use of Common Crawl data is subject to the Common Crawl **Terms of Use**
(<https://commoncrawl.org/terms-of-use>), which the plugin honors — including the
expectation that users comply with those terms and respect the rights of the
crawled sites. No Common Crawl content ships with this plugin; the free path
degrades gracefully (cached or honest "unavailable") when the dataset is
unreachable. See `references/PROVENANCE.md` for the clean-room method.

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
