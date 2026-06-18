# Designer Pro and SEO

A Claude Code plugin for the web-design + SEO workflow: research a niche, generate
a coherent design system, write a complete build brief, build, run a pre-delivery
QA gate, port the result into any CMS, and review on-page SEO. One bundle so the
same project context, scripts, and data libraries serve the whole loop.

All content is **original and clean-room** (see `NOTICE.md` and
`references/PROVENANCE.md`). Free and open source under the **MIT License** — see
`LICENSE`.

## Install

This repository is its own Claude Code **plugin marketplace** (it ships a
`.claude-plugin/marketplace.json`), so installing is two commands in Claude Code:

```text
/plugin marketplace add ZachArticulateV/designer-pro-and-seo
/plugin install designer-pro-and-seo@designer-pro-and-seo
```

Run `/plugin` afterward to confirm `designer-pro-and-seo` is enabled — the skills
are then available in every project. See **QUICKSTART.md** for the five-minute
golden path.

**Developing or contributing?** Load a local clone for the current session instead:

```bash
git clone https://github.com/ZachArticulateV/designer-pro-and-seo
claude --plugin-dir designer-pro-and-seo
```

From a clone you can also run the bundled checks from the repo root —
`python3 scripts/smoke_test.py` (use `py` on Windows).

> **Shipping status (v0.4.x).** **45 of 45 skills are Stable** (real steps, real
> scripts/data, graceful degradation without paid APIs, smoke-tested). Every skill
> that can use an external tool is **tool-aware**: it uses a dedicated MCP/CLI when
> present and falls back to Claude's built-in web/browser tools + bundled scripts
> otherwise (`references/CAPABILITY-TIERS.md`). Skill descriptions describe only what
> the shipping version does. Full status: `SHIPPING.md`.

## Why this plugin exists

Web design and SEO are one workflow in practice but fragmented across tools. This
plugin collapses the loop — research → design → build → SEO → QA → port — into a
single bundle with shared infrastructure, so you stop re-explaining the project to
five disconnected tools.

## Shipping skills (v0.4.x) — 45 stable, mostly free-tier

The whole loop runs end to end on the free tier. Highlights:

- **Design → build → deliver:** `design-system-gen` (CSV-backed Python engine) →
  `design-dimensions` / `design-motion` → `design-build` (renders a real, on-brand,
  accessible HTML page via the engine) → `design-tokens-emit` (CSS/Tailwind/SCSS) →
  `qa-gate` → `portable-html-port` (any CMS). Plus `design-system-persist`,
  `design-cro`, `design-accessibility`, `parallel-build`, `html-extract`,
  `design-research`, `design-visual-qa`.
- **Content:** `copywriting`, `content-draft`, `csv-to-report`.
- **SEO (23):** `seo-audit` orchestrator over `seo-page`, `seo-technical`,
  `seo-schema`, `seo-sitemap`, `seo-image-audit`, `seo-content`, `seo-content-brief`,
  `seo-geo`, `seo-strategy`, `seo-cluster`, `seo-sxo`, `seo-hreflang`, `seo-drift`,
  `seo-competitor-pages`, `seo-programmatic`, `seo-ecommerce`, `seo-local-unified`,
  plus the tool-aware `seo-google`, `seo-dataforseo`, `seo-firecrawl`,
  `seo-backlinks`, `seo-image-gen`.
- **GTM / routing:** `client-outreach`, `route-three-brain`, `route-codex-review`,
  `route-gemini-context`.

Backed by 13 stdlib-only CLI tools (design engine + palette generator, page
renderer, token emitter, HTML porter, CSV profiler, capability probe, and SEO tools
for schema/sitemap/tech-audit/GEO/hreflang/drift), plus a smoke test and a release
verifier — 15 scripts total. From a clone, `python3 scripts/smoke_test.py` verifies
the bundled scripts. See **QUICKSTART.md**.

## Tool-aware, not paid-gated

Every skill that can use an external tool follows a documented **capability-tier
cascade** (`references/CAPABILITY-TIERS.md`): a dedicated MCP/API if connected →
Claude's built-in web/browser tools + bundled scripts → a CLI connector (e.g. the
Gemini CLI for image generation) → a guided manual path. So the formerly
"in-development" skills (`seo-google`, `seo-dataforseo`, `seo-firecrawl`,
`seo-backlinks`, `seo-image-gen`, `design-research`, `design-visual-qa`) all ship
Stable with a real free/built-in path — they just go *deeper* when you connect a tool.

> Routing helpers invoke the `codex` / `gemini` CLIs directly when present (or the
> adjacent `openai-codex` / `cc-gemini-plugin` tools), and degrade to documented
> manual steps when neither is installed — convenience wrappers, not a hard dependency.

## Architecture

```
designer-pro-and-seo/
├── .claude-plugin/          (plugin.json + marketplace.json)
├── skills/                  (each skill its own SKILL.md)
├── scripts/                 (shared stdlib-Python helpers: seo/ design/ workflow/)
├── data/                    (clean-room CSV libraries — see data/README.md)
├── extensions/              (optional MCP wirings, each with setup README + .mcp.json)
├── templates/               (prompt templates and starters)
├── references/              (deep docs loaded on-demand; PROVENANCE ledger; engine contracts)
├── README.md   CLAUDE.md   QUICKSTART.md
├── LICENSE   NOTICE.md   PRIVACY.md   SUPPORT.md   CONTRIBUTING.md
└── RELEASE-NOTES.md
```

## Dependencies

- **Python 3.10+** — for the design reasoning engine and SEO scripts. All shipping
  scripts are **standard library only** — nothing to `pip install`.
- **Optional external tools** — Playwright, Firecrawl, DataForSEO, nanobanana,
  Google APIs. Every skill that can use one also has a **free/reduced path** and
  tells you what the paid path would add. None are required to get value.

## Design principles

- **Original & clean-room.** Bodies, templates, and data are written/generated
  from scratch. Inspiration is allowed; copying is not. See `references/PROVENANCE.md`.
- **Skills compose; they don't duplicate.** Shared logic lives in `scripts/`,
  shared data in `data/`, shared prompts in `templates/`, deep docs in `references/`.
- **Degrade gracefully.** A skill without its optional tool reports what it can
  and names what you'd gain by installing it — it never just fails.
- **Truth in advertising.** A skill's description claims only what its shipping
  body actually does.

## License & legal

**MIT License** — free to use, modify, and redistribute with attribution; see
`LICENSE`. Third-party attributions: `NOTICE.md`. Data handling: `PRIVACY.md`.
Support (via GitHub issues): `SUPPORT.md`.
