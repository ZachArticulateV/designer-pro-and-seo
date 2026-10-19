# AGENTS.md — Operating instructions for any agent in this plugin

This file is the platform-neutral companion to `CLAUDE.md`. Any coding agent that
reads `AGENTS.md` — Codex, Gemini, Cursor, Aider, or another assistant — should treat
the rules here as the contract for working inside the `designer-pro-and-seo` plugin.
It mirrors the role `CLAUDE.md` plays: how the skills in this repo are invoked,
composed, and extended. Where the two files describe the same rule, they must agree;
if they ever drift, that is a bug.

## Core operating principles

1. **Skills compose; they do not duplicate.** A request that spans design + SEO + QA
   is handled by dispatching the relevant skills — sequentially or as parallel
   sub-agents — not by re-implementing one skill's job inside another. Each skill owns
   one capability; orchestrators chain them.

2. **Clean-room originality (hard constraint).** Reference archives — other plugins,
   articles, competitor pages — may be *read* to understand a capability, but never
   copied, transcribed, or paraphrased into this repo. Every skill body, script,
   template, and data row is authored or generated from first principles or from
   public standards. Record provenance in `references/PROVENANCE.md`. Because the repo
   ships publicly under MIT, it must carry no third-party licensed code, copyrighted
   text, or real client/brand names.

3. **Shared infrastructure first.** Before adding a Python helper to a skill, look in
   `scripts/`. Before adding a prompt template, look in `templates/`. Before adding a
   data table, look in `data/`. Reuse over duplication, always.

4. **Originality of voice.** Skill bodies, prompt templates, and README content are
   written from scratch in the project's own voice. External material can inform the
   *idea*; it must never appear as verbatim text.

5. **No source-creator names in skill names.** Skills are named by action and
   capability only. Any attribution to an external concept belongs in commit messages
   and `references/` notes — never in a user-facing skill name.

## Skill families and when to reach for them

| The user wants... | Reach for... |
|---|---|
| Build a website / spin up variants | `parallel-build` → `blast-prompt` → `design-system-gen` → variants |
| Audit a site for SEO | `seo-audit` (dispatches to its sub-skills; for a local build, `scripts/workflow/site_audit.py` is the one-command baseline) |
| Accessibility / WCAG check | `design-accessibility` |
| Port a build to WordPress / GHL / Webflow | `portable-html-port` |
| Pre-delivery / ship-readiness check | `qa-gate` (static path: `scripts/workflow/qa_gate.py --report`) |
| Review code the agent just wrote | `route-codex-review` — route to a *different* model, never self-review |
| Whole-repo or long-file analysis | `route-gemini-context` |
| Pick colors / fonts / a style | `design-system-gen` then `design-dimensions` |
| Competitor comparison pages | `seo-competitor-pages` |
| Detect SEO regressions since last deploy | `seo-drift` |

## Parallel build pattern (encoded once, reused everywhere)

`parallel-build` is the reusable 3-variant build primitive:

1. Capture the brief (target business, 3 inspiration sources).
2. Create 3 isolated worktrees or sibling output folders.
3. Dispatch 3 parallel sub-agents — same brief, a different inspiration source each.
4. Each sub-agent runs `design-system-gen` first so variants share token consistency.
5. Each does a one-shot build, iterating only when needed.
6. Return a side-by-side comparison; the user cherry-picks sections to merge.

Other build-style skills (e.g. `design-build`) call this pattern when the user
explicitly asks for variants.

## QA gate as mandatory pre-delivery

For any client-bound deliverable, `qa-gate` is the final step before handoff. It emits
a structured PASS / CONDITIONAL PASS / FAIL report with Risk Rating
(Low / Med / High / Critical), Critical Issues, Warnings, Recommendations,
Nice-to-Haves, Estimated Fix Time, and Client-Ready Status. Do not skip this gate when
delivering work that leaves the building.

## Routing law (no model reviews its own output)

`route-three-brain` codifies the hand-off:

- **Driver** — the primary agent generates code, content, and design.
- **Adversarial reviewer** — a *different* model (Codex / GPT-class) does correctness
  review, second-opinion debugging, and deep checking.
- **Long-context analyst** — a high-context model (Gemini-class) handles repo-wide
  reads and multi-document synthesis.

The load-bearing rule: **no model reviews its substantive own output.** Same
architecture means the same blind spots, so a self-review catches nothing that
matters. When the user says "check your work" / "review this" / "is this right" —
route to a different model via `route-codex-review`. This holds whichever agent is the
driver: the reviewer must not be the author.

## Scripts, data, extensions

- `scripts/seo/` — one engine per SEO specialist: technical, content, schema + entity
  graph, sitemap + link graph, images, GEO + llms.txt + the shared AI-crawler registry,
  hreflang, e-commerce, drift, clustering, local. Standard library only.
- `scripts/design/` — the design-system reasoning engine (CSV-backed scoring) plus the
  accessibility, CRO and motion audits.
- `scripts/workflow/` — orchestrators and plumbing: `site_audit.py` (one-command SEO
  health score), `qa_gate.py` (one-command pre-delivery gate), the score fan-in, the
  shared SSRF guard, the cost guard, the HTML porter, the CSV profiler.
- Every folder carries its own `README.md` — start at `README.md` → "Repository map".
- `data/` — CSV libraries (UI styles, palettes, fonts, UX rules, product types).
- `extensions/` — optional MCP wirings; each subfolder's README explains setup.
- `templates/` — prompt templates skills reference (BLAST, 5-Dimensions, design-system
  starter, and so on).
- `references/` — deep docs loaded on demand so `SKILL.md` bodies stay lean.

**Invoking bundled scripts.** Skill bodies call scripts via
`${CLAUDE_PLUGIN_ROOT}/scripts/...` — the variable resolves to the plugin's install
directory wherever it lands, so a bare `scripts/...` path (which points at the user's
own project) is wrong in a shipped skill. On Windows the Python launcher is `py` when
`python3` is absent; in PowerShell the variable is `$env:CLAUDE_PLUGIN_ROOT`. When
developing inside this repo (plugin not yet installed), run scripts with bare
`scripts/...` paths from the repo root — exactly what `scripts/smoke_test.py` and
`scripts/verify_release.py` do.

## Authoring contracts (read before touching any skill)

Every skill body, script, and template follows `references/ENGINE-CONTRACTS.md`. The
load-bearing rules:

- **SKILL.md section order is fixed**, and `Dependencies` always precedes `Notes`.
- **Triggers are domain-qualified** — never a bare generic verb (`audit`, `review`,
  `generate`); cross-domain `route-*` skills scope triggers to their own lane.
- **The dependency graph is a DAG** — edges run orchestrator → specialist, never back.
  Mutual relationships live under `Notes ("Related skills")`, not Dependencies.
- **Graceful degradation** — every skill that can use an optional paid tool also ships
  a free path and detects the tool at runtime. The free path is the product.
- **Standard-library-only Python** — `scripts/` add no runtime dependency; declare any
  unavoidable exception in a per-folder `requirements.txt`.
- **Secrets** — environment variables only; never log keys; never write client data
  outside the user's workspace.
- **Status truth** — a skill is `Stable` only once the `SHIPPING.md` promotion
  checklist passes; everything else is `In development` and says so in its description.
  A description claims only what the shipping body actually delivers.

## Version + change discipline

- Bump `plugin.json` `version` (and `marketplace.json`) on every meaningful change.
- Append an entry to `RELEASE-NOTES.md` for each version.
- `SHIPPING.md` is the source of truth for skill status; keep it, the per-skill
  `**Status:**` lines, and the descriptions in sync.
- Keep both gates green before "done": `scripts/smoke_test.py` and
  `scripts/verify_release.py`.

## Drift note

This file and `CLAUDE.md` describe the same plugin from the same rule set. Edit them
together: when a core rule changes in one, change it in the other so a consistency
check across the two never fails.
