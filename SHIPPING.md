# Shipping Manifest

The single source of truth for what this plugin **does today** versus what is
**designed but not yet released**. Skill descriptions and bodies are kept in sync
with this file. (See README for the narrative version.)

Legend: ✅ Stable (built, verified, supported) · 🟡 In development (scaffolded,
not released, excluded from functional claims & support).

Total skills: 45 (**45 ✅ Stable**, 0 🟡 In development).

## ✅ Shipping (v0.4.x) — 45 skills

**Design (10):** `design-system-gen`, `design-dimensions`, `design-motion`,
`design-system-persist`, `design-build`, `design-tokens-emit`, `design-cro`,
`design-accessibility`, `design-research`, `design-visual-qa`

**Build & QA (5):** `blast-prompt`, `qa-gate`, `portable-html-port`,
`parallel-build`, `html-extract`

**Content & data (3):** `copywriting`, `content-draft`, `csv-to-report`

**Business / GTM (1):** `client-outreach`

**Routing (3):** `route-three-brain`, `route-codex-review`, `route-gemini-context`

**SEO (23):** `seo-page`, `seo-image-audit`, `seo-technical`, `seo-schema`,
`seo-sitemap`, `seo-audit`, `seo-content`, `seo-content-brief`, `seo-geo`,
`seo-strategy`, `seo-cluster`, `seo-sxo`, `seo-hreflang`, `seo-drift`,
`seo-competitor-pages`, `seo-programmatic`, `seo-ecommerce`, `seo-local-unified`,
`seo-google`, `seo-dataforseo`, `seo-firecrawl`, `seo-backlinks`, `seo-image-gen`

Most are free-tier; optional paid tools (DataForSEO, Playwright, Google APIs) only
*deepen* them. Each skill that can use one is **tool-aware** and has a documented
free/built-in path — see `references/CAPABILITY-TIERS.md`.

## 🟡 In development — 0 skills

None. As of v0.4.0 every skill is Stable. The seven formerly-in-development skills
were reworked onto the **capability-tier cascade** (`references/CAPABILITY-TIERS.md`):
each uses a dedicated MCP/CLI when present and falls back to Claude's built-in
web/browser tools + bundled scripts otherwise, so none hard-depends on a paid tool.

> Note: `design-visual-qa` requires a browser to capture screenshots and uses the
> **free, bundled** Playwright extension (plus Claude's vision to compare); without
> it, it delivers a manual visual-QA checklist. It is Stable because its enabling
> tool is free and bundled, not a paid gate.

## Shipping scripts (all stdlib-only, smoke-tested)

`scripts/smoke_test.py` verifies the install (36/36) and `scripts/verify_release.py`
is the release gate. The 13 CLI tools (15 scripts total, counting those two):
`design/design_system.py`, `design/gen_palettes.py`, `design/render_page.py`,
`design/tokens_emit.py`, `workflow/portable_html.py`, `workflow/csv_to_report.py`,
`workflow/capability_probe.py`, `seo/schema_gen.py`, `seo/sitemap_tools.py`,
`seo/tech_audit.py`, `seo/geo_check.py`, `seo/hreflang_tools.py`,
`seo/drift_tools.py`.

## Promotion checklist (🟡 → ✅)

A skill ships only when **all** are true:
1. `Steps` are real and executable (no "TBD").
2. Every script/data/template it references **exists** in the repo.
3. It **degrades gracefully** without optional paid tools (free path documented).
4. Its description claims **only** what the body delivers, no "In development"
   marker, and `**Status:**` reads `Stable`.
5. Verification by type: script/data-backed skills pass `scripts/smoke_test.py`;
   method-only skills contain a complete worked method.
