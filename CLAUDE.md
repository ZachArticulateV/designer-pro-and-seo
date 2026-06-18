# CLAUDE.md — Operating instructions for Claude in this plugin

This file is loaded by Claude Code when working inside the `designer-pro-and-seo` plugin. It defines how skills here should be invoked, composed, and extended.

## Core operating principles

1. **Skills compose; they do not duplicate.** If a request spans design + SEO + QA, dispatch the relevant skills in sequence or in parallel sub-agents — do not try to do everything inside one skill.

2. **Clean-room originality.** Inspiration archives (other plugins, articles) may be *read* to understand a capability, but never copied, transcribed, or "lightly rewritten" into this plugin. Every body, script, template, and data row is authored/generated from scratch. Record provenance in `references/PROVENANCE.md`. This is a hard constraint — the repo ships publicly on GitHub, so it must contain no third-party licensed code, copyrighted text, or real client/brand names.

3. **Shared infrastructure first.** Before adding a Python helper to a skill, check `scripts/`. Before adding a prompt template, check `templates/`. Before adding CSV data, check `data/`. Reuse over duplication.

4. **Originality requirement.** Skill bodies, prompt templates, and README content here must be written from scratch in Zach's voice — they may take inspiration from external sources but must not be verbatim copies.

5. **No source-creator names in skill names.** Skills are named by action and capability only. Source attribution belongs in commit messages and `references/` notes, not in user-facing names.

## When to use which family

| User says... | Reach for... |
|---|---|
| "Build a website" / "spin up variants" | `parallel-build` → `blast-prompt` → `design-system-gen` → variants |
| "Audit this site for SEO" | `seo-audit` (which dispatches to sub-skills) |
| "Check accessibility" / "WCAG" | `design-accessibility` |
| "Make this site work in WordPress / GHL / Webflow" | `portable-html-port` |
| "Pre-delivery check" / "is this ready to ship" | `qa-gate` |
| "Review this code" (after Claude wrote it) | `route-codex-review` — MUST route to Codex, never self-review |
| "Long file analysis" / "scan the whole repo" | `route-gemini-context` |
| "Pick colors / fonts / a style" | `design-system-gen` then `design-dimensions` |
| "Make competitor comparison pages" | `seo-competitor-pages` |
| "Track if SEO regressed since last deploy" | `seo-drift` |

## Parallel build pattern (encoded once, reused everywhere)

The `parallel-build` skill encodes the 3-variant build workflow as a reusable primitive:

1. Capture brief (target client/business, 3 inspiration sources)
2. Create 3 git worktrees or sibling output folders
3. Dispatch 3 parallel sub-agents, each with a different inspiration source and the same brief
4. Each sub-agent runs `design-system-gen` first so all variants share token consistency
5. Each sub-agent does a one-shot build (iterate only if needed)
6. Return side-by-side comparison; user cherry-picks sections from each to merge

Other build-style skills (e.g. `design-build`) call this pattern when the user explicitly wants variants.

## QA gate as mandatory pre-delivery

For any client-bound deliverable, `qa-gate` is the final step before handoff. It produces a structured PASS / CONDITIONAL PASS / FAIL report with Risk Rating (Low / Med / High / Critical), Critical Issues, Warnings, Recommendations, Nice-to-Haves, Estimated Fix Time, and Client-Ready Status. Never skip this gate when delivering to a paying client.

## Routing law

`route-three-brain` codifies when to hand off:
- **Claude** — primary driver for code, content, design generation
- **Codex (GPT-5.5)** — adversarial review, second-opinion debugging, deep correctness checking
- **Gemini 2.5 Pro** — long-context (1M+ tokens) repo-wide analysis, multi-document synthesis

Never let Claude review its own substantive output. If the user says "check your work" / "review this" / "is this right" — route to Codex via `route-codex-review`.

## Scripts, data, extensions

- `scripts/seo/` — Python helpers for SEO: schema gen/validate, sitemap tools, technical audit, GEO citability, hreflang, drift. Written from scratch; standard library only.
- `scripts/design/` — design system reasoning engine (CSV-backed scoring). Written from scratch.
- `scripts/workflow/` — orchestrators for `parallel-build`, `qa-gate`, `csv-to-report`.
- `data/` — CSV libraries (UI styles, palettes, fonts, UX rules, product types).
- `extensions/` — optional MCP wirings. Each subfolder has a README explaining setup.
- `templates/` — prompt templates referenced by skills (BLAST template, 5-Dimensions template, design system starter, etc.).
- `references/` — deep documentation that skills load on-demand (avoids bloating SKILL.md bodies).

**Invoking bundled scripts.** Skill bodies call scripts as
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/..."`. `${CLAUDE_PLUGIN_ROOT}` is the
environment variable Claude Code sets to the plugin's install directory, so the path
resolves wherever the plugin is installed — not the user's current working directory
(a bare `scripts/...` path would look inside the user's own project and fail). On
Windows use `py` if `python3` is absent; in PowerShell the variable is
`$env:CLAUDE_PLUGIN_ROOT`. When developing inside this repo (plugin not yet
installed), run scripts with bare `scripts/...` paths from the repo root — that is
what `scripts/smoke_test.py` and `scripts/verify_release.py` do.

## Authoring contracts (read before touching any skill)

All skill bodies, scripts, and templates follow `references/ENGINE-CONTRACTS.md`.
The load-bearing rules:

- **SKILL.md section order** is fixed; `Dependencies` always precedes `Notes`.
- **Trigger qualification** — never list a bare generic verb (`audit`, `review`,
  `generate`); always domain-qualify it. Cross-domain `route-*` skills scope their
  triggers to their own lane.
- **Dependency graph is a DAG** — `Dependencies` go orchestrator → specialist,
  never back. Mutual relationships go under `Notes ("Related")`, not Dependencies.
- **Graceful degradation** — every skill that can use an optional paid tool also
  has a free path and detects the tool at runtime. The free path is the product.
- **Secrets** — env vars only; never log keys; never write client data outside the
  user's workspace.
- **Status truth** — `Stable` only when the promotion checklist in `SHIPPING.md`
  passes. Everything else is `In development` and carries the marker in its
  description. A skill's description claims only what its shipping body delivers.

## Version + change discipline

- Bump `plugin.json` `version` on every meaningful change.
- Append to `RELEASE-NOTES.md` for each version.
- `SHIPPING.md` is the source of truth for skill status. Keep it, the skill
  `**Status:**` lines, and the descriptions in sync.
