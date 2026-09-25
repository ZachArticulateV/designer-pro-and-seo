# Shipping Manifest

The single source of truth for what this plugin **does today** versus what is
**designed but not yet released**. Skill descriptions and bodies are kept in sync
with this file. (See README for the narrative version.)

Legend: ✅ Stable (built, verified, supported) · 🟡 In development (scaffolded,
not released, excluded from functional claims & support).

Total skills: 45 (**45 ✅ Stable**, 0 🟡 In development). Depth: **16 Core · 26 Lite ·
3 routing** (see [Depth tiers](#depth-tiers-core--lite--routing--a-partition-of-the-45)).

## ✅ Shipping (v1.4.0) — 45 skills

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

## Depth tiers (Core / Lite / routing) — a partition of the 45

Orthogonal to Stable, every Stable skill also sits in one **depth tier** — the honest
"how deep is it" signal introduced with v1 "Deep Core."

- **Core (16)** — deepened this release into a real 3-layer skill: earned per-skill
  `references/` and/or a wired dispatch layer (real Agent-tool fan-out, plus the
  flagship differentiators). These are the skills v1 raises to a higher level.
- **Lite (26)** — Stable, with a real free/built-in path, but single-file; slated for
  the same depth pass in **v1.1 "Depth Sweep."** Lite means "not yet 3-layer," not
  "lesser quality."
- **Routing (3)** — the three-brain hand-off skills (Claude drives; Codex reviews;
  Gemini long-context).

The three lists **partition the 45 skills on disk exactly** — the release gate (C10)
fails if any skill is missing, invented, or double-counted, so the count claim is
mechanically un-fakeable.

```depth-tiers
core:    design-system-gen, design-build, design-research, design-accessibility, design-visual-qa, qa-gate, parallel-build, portable-html-port, seo-audit, seo-cluster, seo-drift, seo-geo, seo-local-unified, seo-strategy, seo-technical, seo-schema
lite:    design-dimensions, design-motion, design-system-persist, design-tokens-emit, design-cro, blast-prompt, html-extract, copywriting, content-draft, csv-to-report, client-outreach, seo-page, seo-sitemap, seo-image-audit, seo-content, seo-content-brief, seo-sxo, seo-hreflang, seo-competitor-pages, seo-programmatic, seo-ecommerce, seo-google, seo-dataforseo, seo-firecrawl, seo-backlinks, seo-image-gen
routing: route-three-brain, route-codex-review, route-gemini-context
```

**45 Stable = 16 Core + 26 Lite + 3 routing.**

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

`scripts/smoke_test.py` verifies the install (38/38) and `scripts/verify_release.py`
is the release gate. Every other script is a standalone CLI **and** an importable
library (`design/match.py` is library-only, the ranker behind `design_system.py`):

- **design/** — `a11y_static`, `design_system`, `gen_charts`, `gen_palettes`, `match`,
  `render_page`, `tokens_emit`
- **seo/** — `ai_crawlers` (the one AI-crawler registry + RFC 9309 robots evaluator),
  `business_type`, `crawl_inventory`, `drift_baseline` / `drift_compare` /
  `drift_history` / `drift_severity` / `drift_tools`, `geo_check`, `geogrid`,
  `hreflang_tools`, `llms_txt` (llms.txt generate/validate), `nap_check`, `page_fetch`, `schema_gen`, `serp_cluster`,
  `site_map`, `sitemap_tools`, `tech_audit`
- **workflow/** — `audit_aggregate`, `capability_probe`, `cost_guard`, `csv_to_report`,
  `net_safety` (the one shared SSRF guard), `portable_html`

Dated search facts every SEO skill relies on live in one file,
`references/shared/search-landscape-2026.md` (reviewed quarterly).

## Promotion checklist (🟡 → ✅)

A skill ships only when **all** are true:
1. `Steps` are real and executable (no "TBD").
2. Every script/data/template it references **exists** in the repo.
3. It **degrades gracefully** without optional paid tools (free path documented).
4. Its description claims **only** what the body delivers, no "In development"
   marker, and `**Status:**` reads `Stable`.
5. Verification by type: script/data-backed skills pass `scripts/smoke_test.py`;
   method-only skills contain a complete worked method.

### Core promotion (✅ Stable → **Core**)

A Stable skill earns the **Core** depth tier only when it is genuinely 3-layer:

6. **Orchestrator parity (C3)** — if it dispatches, every specialist it names resolves
   to an agent on disk (and is itself wired), and the dispatch shape is derived, not
   mirrored.
7. **Free-path proof (C4)** — its Tier-2 names a real on-disk script exercised by a
   golden example under `references/examples/` (or is C4-exempt-by-spec).
8. **Depth proof (C1 + C5)** — every cited `references/…` path resolves, and any
   dispatched-leaf agent passes least-privilege.

Everything Stable-but-single-file stays **Lite** until it earns this pass (v1.1).
