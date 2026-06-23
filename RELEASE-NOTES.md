# Release Notes

## v0.4.2 — 2026-06-22 — judge-panel correctness pass

Acted on a multi-judge review (six specialist judges + an adversarial red-team).
Six confirmed, non-destructive fixes; the aggressive cuts the red-team flagged as
destructive (cut `seo-page`, cut the `route-*` skills, split the plugin) were
deliberately *not* taken. Codex-reviewed; gates green (smoke 36/36, release gate
23/23).

### Correctness fixes
- **design engine honors explicit style keywords.** A keyword naming a different
  style than the product default (e.g. `brutalist` on a saas-landing) was silently
  ignored — the engine returned the default with an empty `_fallbacks`, violating its
  own honesty contract. Keywords that name a style now win and the swap is recorded in
  `_fallbacks`.
- **`tokens_emit.py` creates a fresh `--out-dir`.** The primary file-emitting path
  failed on a clean first invocation (no `os.makedirs`); it now creates the directory.
- **`geo_check.py` no longer false-negatives short sourced stats.** A 15-word floor
  rejected the densest, most-citable passages (a one-sentence claim with a number,
  date, and named source). The floor is removed for passages that are specific and
  standalone.
- **`tech_audit.py` exits non-zero on a missing `--file`** (and surfaces the error)
  instead of silently returning an empty report with exit 0.

### Truth-in-advertising + triggers
- **`seo-audit`** now reflects that all specialists are shipped/Stable: it dispatches a
  core on-page set always and adds `seo-content`/`seo-geo` plus business-type and
  tool-gated specialists conditionally — removing the stale "until they ship" prose
  that contradicted the 45/45-Stable claim.
- **Trigger de-duplication.** Removed the duplicated `"second opinion"` phrase from
  `route-three-brain`'s trigger list (it stays on `route-codex-review`), and added a
  reciprocal `"AI visibility"` disambiguator between `seo-geo` (optimize, free) and
  `seo-dataforseo` (measure, paid).

### Tests
- Four regression guards added to `scripts/smoke_test.py` (one per code fix); smoke is
  now 36/36.

## v0.4.1 — 2026-06-17 — installable + audit fixes

Acted on a full external audit (five deep-dive agents + a plugin-spec conformance
pass). Two blockers the plugin's own gates couldn't see are fixed, so it now actually
installs and runs; the rest is correctness polish. Codex-reviewed; gates green
(smoke 32/32, release gate 23/23).

### Blockers fixed
- **Bundled scripts now resolve when installed.** Every script-backed skill invoked
  its script with a bare `python3 scripts/...` path, which resolves against the
  user's project, not the plugin — so the engine failed on a real install. All 18
  skill invocations now use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/..."` (the
  documented env var); a new release-gate check forbids the bare form from returning.
- **The repo is now its own marketplace.** Added `.claude-plugin/marketplace.json`
  (source `./`) and rewrote the README/QUICKSTART Install sections to the real flow —
  `/plugin marketplace add ZachArticulateV/designer-pro-and-seo` then
  `/plugin install designer-pro-and-seo@designer-pro-and-seo` (plus `--plugin-dir`
  for contributors).

### Graph, scripts & data correctness
- Broke the `design-build` <-> `parallel-build` cycle and the `seo-strategy` ->
  `seo-audit` back-edge (DAG contract); the reverse edges moved to Notes.
- Script input robustness: missing files / malformed JSON now return a JSON error +
  exit 1 instead of a traceback (csv_to_report, drift_tools, hreflang_tools,
  render_page, tokens_emit); design_system tolerates a non-UTF-8 data CSV.
- csv_to_report: "1,5" is no longer misread as 15; the numeric-column gate is a true
  80% (ceil, not int); duplicate headers are flagged.
- tech_audit: a real robots.txt `Disallow: /` check (group precedence) replaces the
  old "merely mentions GPTBot" flag.
- render_page escapes interpolated section text; portable_html adds the advertised
  `carrd` target (smoke 31 -> 32).

### Truth-in-advertising & hygiene
- README "14 scripts" -> "13 CLI tools / 15 total" (a gate check now reconciles it);
  SHIPPING lists `capability_probe.py`; the GEO citation in seo-geo is corrected (not
  "CMU"); design-tokens-emit no longer implies a `MASTER.md` is directly consumable;
  "byte-for-byte" -> newline-normalized.
- Retired `REFUNDS.md`; added `CONTRIBUTING.md`; gitignored internal `docs/`.
- New release-gate checks: `${CLAUDE_PLUGIN_ROOT}` script paths, marketplace.json +
  version match, and script-count reconciliation; fixed the version check so `v0.4`
  no longer matches `v0.41`. Gate 18 -> 23 checks.

## v0.4.0 — 2026-06-16 — 45/45 stable, tool-aware backbone, free GitHub release

Hardened the plugin from "38 of 45 stable" to **45 of 45**, reframed it as a **free,
MIT-licensed plugin for public GitHub release**, and added a release gate so the
state stays honest. Three-brain throughout (Claude builds, Codex adversarial code
review, Gemini long-context).

### Tool-aware capability backbone (the headline)
- New `references/CAPABILITY-TIERS.md`: a four-tier cascade — dedicated MCP/API →
  Claude built-in web/browser + bundled scripts → CLI connector (e.g. Gemini CLI) →
  guided manual path. The free/built-in path is the product; tools only deepen it.
- New `scripts/workflow/capability_probe.py` (stdlib): detects available CLIs/env
  (never emits secret values; always exits 0).
- Reworked all **7 formerly-in-development skills** onto the cascade and promoted
  each to Stable: `seo-google`, `seo-dataforseo`, `seo-firecrawl`, `seo-backlinks`,
  `seo-image-gen` (Gemini CLI prioritized for rendering), `design-research`,
  `design-visual-qa`. None hard-depends on a paid tool anymore.

### Free-distribution fit
- Replaced the placeholder commercial license with the **MIT License**; set
  `plugin.json` license/homepage/repository. SUPPORT/PRIVACY/NOTICE now point to
  GitHub issues; REFUNDS repurposed to a free-plugin note; README gained an install
  section.

### Clean-room & truth-in-advertising
- Completed `references/PROVENANCE.md` (now records all shipping scripts, was 5/13).
- **Excised a real client name** from `design-research` (public-repo safety).
- Reconciled every count/version across README, SHIPPING, QUICKSTART, plugin.json,
  and skill Status lines; fixed stale "5/5"/"six skills"/"v0.2.x" claims.

### Hardening, tests & CI
- Cross-platform encoding guard on all 13 CLI scripts (no cp1252 `UnicodeEncodeError`).
- Smoke test deepened 15 → **31 checks**, including a golden-fixture regression oracle.
- New `scripts/verify_release.py` release gate (smoke + doc/provenance/clean-room/
  config consistency) + `.github/workflows/verify.yml` (Windows+Linux × Py3.10/3.13).
- Codex adversarially reviewed every new/changed script; findings fixed and re-verified.

> Note: `design-visual-qa` is Stable on the basis that its enabling tool (Playwright)
> is **free and bundled**, with Claude-vision comparison and a manual-checklist
> fallback — not a paid gate.

## v0.3.0 — 2026-06-03 — 38 stable skills, researched best practices, 12 tools

Took the plugin from 12 stable skills to **38 of 45**, with current (2026)
best practices researched per use case and real stdlib tooling behind the SEO and
design families. Three-brain throughout (Claude builds, Gemini long-context, Codex
adversarial code review).

### New tooling (all stdlib-only, smoke-tested — 15/15)
- **Design:** `render_page.py` (renders a real, on-brand, accessible single-file
  HTML page from the design-system engine — the unique design→artifact→port loop),
  `tokens_emit.py` (CSS / Tailwind / SCSS / Style-Dictionary tokens).
- **SEO:** `schema_gen.py` (JSON-LD generate + validate vs Google's required props,
  flags the 2026 FAQ-rich-result deprecation), `sitemap_tools.py` (generate/validate,
  50k-URL index splitting), `tech_audit.py` (9-dimension technical checks; INP<200ms,
  AI-crawler robots policy, security headers), `geo_check.py` (passage-citability
  scoring + llms.txt/AI-crawler checks), `hreflang_tools.py` (validate/generate),
  `drift_tools.py` (SEO baseline + diff).

### Promoted to Stable (26 skills, in 5 batches)
- **SEO technical core:** seo-technical, seo-schema, seo-sitemap, seo-audit.
- **Design:** design-build (renderer-backed), design-tokens-emit, design-cro,
  design-accessibility, design-system-persist, design-motion.
- **Content/GEO:** seo-content, seo-content-brief, seo-geo, seo-strategy,
  seo-cluster, seo-sxo, copywriting, content-draft, csv-to-report.
- **Specialized SEO:** seo-hreflang, seo-drift, seo-competitor-pages,
  seo-programmatic, seo-ecommerce, seo-local-unified, seo-image-audit.
- **Build/GTM/routing:** parallel-build, html-extract, client-outreach,
  route-three-brain, route-codex-review, route-gemini-context.

### Researched best practices baked in
- CWV LCP<2.5s / CLS<0.1 / **INP<200ms** (most-failed metric).
- robots.txt: block AI *training* crawlers, allow *retrieval* bots (stay citable).
- Schema: JSON-LD only; **FAQ rich results deprecated 2026-05-07**.
- GEO: passage citability (specificity + standalone), llms.txt, structured-data as a
  top-5 citation factor.

### Still In development (7) — need external paid API/MCP/browser
seo-google, seo-dataforseo, seo-firecrawl, seo-backlinks, seo-image-gen,
design-research, design-visual-qa.

### Hardening
Codex adversarial review of all new scripts; findings triaged and integrated.
All clean-room (PROVENANCE updated). `SHIPPING.md`, `README.md`, and `QUICKSTART.md`
updated to the 38-stable state.

## v0.2.0 — 2026-06-02 — Legal quarantine, functional MVP, hardening

A major step from "scaffold" to "a small, real, sellable core." Built across a
structured roadmap with three-model review (Claude driver, Gemini long-context
structural pass, Codex adversarial code review).

### Legal & provenance (sale-readiness)
- Removed all third-party plugin names from `plugin.json`, `README.md`, `CLAUDE.md`,
  and skill bodies (clean-room positioning).
- Replaced the data plan that referenced another plugin's source with an
  independent, reproducible clean-room data layer; added a per-asset
  `references/PROVENANCE.md` ledger.
- Replaced the MIT license with a placeholder **commercial license** (`LICENSE`),
  flagged for final legal review.
- Added `NOTICE.md`, `PRIVACY.md`, `SUPPORT.md`, `REFUNDS.md`.
- Renamed the third-party "FLOW" methodology to an original **Evidence Loop**.

### Truth in advertising
- Introduced `SHIPPING.md` as the source of truth for skill status.
- Marked all not-yet-functional skills **In development** (status line + a marker
  in the description) so the picker never surfaces a false capability claim.

### Functional MVP — 12 Stable skills
- **Design:** `design-system-gen` (CSV-backed Python engine), `design-dimensions`,
  `design-motion`, `design-system-persist`.
- **Build & QA:** `blast-prompt`, `qa-gate`, `portable-html-port`.
- **Content:** `copywriting`, `content-draft`, `csv-to-report`.
- **SEO:** `seo-page`, `seo-image-audit`.
- Built the engine (`scripts/design/design_system.py`), a reproducible palette
  generator (`gen_palettes.py`), a security-hardened HTML inliner
  (`portable_html.py`), and a CSV profiler (`csv_to_report.py`).
- Built 5 clean-room data libraries and 4 prompt templates.
- Wired real `.mcp.json` configs for Playwright, DataForSEO, Firecrawl, nanobanana,
  each with graceful-degradation docs.

### Structure & polish
- Split `seo-images-unified` into `seo-image-audit` + `seo-image-gen`.
- Added Tier A coverage: `copywriting`, `content-draft`, `design-motion`.
- Fixed the real circular dependency (`seo-content` ↔ `seo-geo`).
- Scoped routing-review triggers so they can't hijack SEO-audit requests.
- Added `references/ENGINE-CONTRACTS.md` (interface spec) and codified conventions
  in `CLAUDE.md`.

### Hardening (from Codex adversarial review)
- **Security:** `portable_html.py` now refuses absolute/`..` paths (prevents
  exfiltrating files like `../secret.env` into output) — verified.
- **Privacy:** `csv_to_report.py` redacts sensitive-looking columns by default and
  falls back across encodings — verified.
- `design_system.py` flags weak matches instead of silently returning an arbitrary
  row; palettes now include a contrast-safe `on_primary` color.
- Added `scripts/smoke_test.py` (install verification, 5/5 passing) and golden
  examples under `references/examples/`.

### Counts
45 skills total: **12 Stable**, 33 In development.

---

## v0.1.0 — 2026-05-17 — Initial scaffold

Plugin folder tree created. All skill folders + SKILL.md stubs in place with
frontmatter, family classification, intent, and triggers. Shared-infrastructure
folders scaffolded with explanatory READMEs. Skill bodies were stubs; scripts and
data libraries were empty.
