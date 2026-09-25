# Release Notes

## v1.8.0 — 2026-09-25 — seo-hreflang + seo-ecommerce promoted to Core (loop cycle 8 of 10)

**22 Core · 20 Lite · 3 routing.**
- **`hreflang_tools.py`**: the full ISO 639-1 list, ISO 15924 script subtags
  (`zh-Hant-TW`), and fix-it hints for the classic mistakes (`en-uk`→`GB`, `jp`→`ja`,
  numeric `es-419`, `EU`). New **`--cluster`** audit across pages (manifest
  `{url: file}` or files with canonicals): missing annotations, invalid codes,
  self-reference, **return links**, one code per URL, x-default presence +
  consistency, `<html lang>` agreement, noindex alternates, cross-locale canonicals —
  codes H1–H12 with a score. `x-default` is correctly excluded from self-reference and
  return-link checks (caught by the new tests).
- **New `scripts/seo/product_audit.py`**: merchant-listing readiness with
  **markup-vs-page agreement** (price visible — cents must match, rating visible,
  InStock vs "sold out"), expired `priceValidUntil`, availability, GTIN/MPN/brand,
  return policy (Offer or Organization) and shipping details, variants without a
  ProductGroup, H1, thin copy (P1–P14, reusing `schema_gen.py`); category hygiene —
  self-canonical indexable facets, page N → page 1 canonicals, noindexed pagination,
  indexable sort URLs, thin category copy, ItemList (C1–C6).
- New references `references/seo-hreflang/cluster-rules.md` and
  `references/seo-ecommerce/merchant-checks.md`; golden examples for both (hreflang
  68/100; product 40/100, category 86/100 — pinned).
- Gates: smoke 38/38, 616 unit tests (+15 in `tests/test_hreflang_commerce.py`),
  verify_release 56/56.

## v1.7.0 — 2026-09-25 — seo-image-audit promoted to Core (loop cycle 7 of 10)

**20 Core · 22 Lite · 3 routing.** Image SEO moves from a by-hand checklist to an engine.
- **New `scripts/seo/image_audit.py`** — per-finding-type audit listing the affected
  images: alt quality (missing, decorative without `alt=""`, **linked image with empty
  alt = nameless link**, file name as alt, "image of…", > 125 chars, keyword-stuffed,
  reused), legacy formats without a WebP/AVIF alternative (`<picture>` / srcset aware),
  `srcset` missing or without `sizes`, LCP loading (lazy hero, several / no
  `fetchpriority=high`, below-fold not lazy), CLS dimensions, camera/hash file names,
  and `og:image`. With `--assets` it reads **real bytes and intrinsic pixels from the
  image headers** (PNG, GIF, JPEG, WebP VP8/VP8L/VP8X, AVIF — pure stdlib, traversal
  guarded) for byte budgets, oversize and aspect-mismatch checks; without it those land
  in `needs_data` instead of being guessed. Emits `cwebp` / `avifenc` / `magick`
  commands; never converts files. Score 0-100.
- The `seo-image-audit` agent moves from WebFetch to the bundled SSRF-guarded fetcher
  (least privilege preserved) and now reports a real score.
- New `references/seo-image-audit/image-rubric.md`; golden example
  `references/examples/seo-image-audit/` with generated PNG assets (48/100, pinned).
- Gates: smoke 38/38, 601 unit tests (+12 in `tests/test_image_audit.py`),
  verify_release 56/56.

## v1.6.0 — 2026-09-25 — seo-sitemap promoted to Core + internal-link graph (loop cycle 6 of 10)

**19 Core · 23 Lite · 3 routing.** The "live quality gates" step that used to be manual
is now a script, and internal linking gets its own engine.
- **`sitemap_tools.py`**: `.xml.gz` support; host / scheme / duplicate / fragment /
  tracking-parameter hygiene; **lastmod honesty** (W3C format, future dates with
  `--as-of`, >90% identical = auto-bumped); changefreq/priority flagged as ignored;
  image / video / news (1,000 cap, 2-day freshness) / hreflang `xhtml:link` (absolute,
  self + return links) extension checks; codes S01–S26 with a score. New
  **`--crosscheck`** quality gates against page states (G1 4xx/5xx, G2 redirect, G3
  noindex, G4 canonical-elsewhere, G5 indexable page missing) and **`--check-live`**
  (SSRF-guarded sample fetch that states "fetched N of M"). `--generate` dedupes,
  accepts real per-URL dates via `--lastmod-file`, and warns on a blanket `--lastmod`.
- **New `scripts/seo/link_graph.py`** — internal-link graph from a static build
  (`--dir`) or a crawler export (`--edges`): orphans, islands unreachable from home,
  BFS click depth (> 3 flagged), broken internal targets (downgraded to info when the
  page set is incomplete), dead ends, nav/footer-only pages, generic-anchor-only pages,
  internal nofollow, sitemap parity. Codes L0–L10 with a score.
- New `references/seo-sitemap/gates-and-architecture.md`; the golden example gains a
  9-page static site + `pages.json` (gates 82/100, link graph 64/100 — pinned).
- Gates: smoke 38/38, 589 unit tests (+14 in `tests/test_sitemap_linkgraph.py`),
  verify_release 56/56.

## v1.5.0 — 2026-09-25 — seo-page + seo-content promoted to Core (loop cycle 5 of 10)

**18 Core · 24 Lite · 3 routing.** Both skills now run a real, deterministic engine
instead of a by-hand checklist.
- **New `scripts/seo/content_audit.py`** — HTML / Markdown / text in; eight dimensions
  out, each finding with a fix, plus a 0-100 content score:
  E-E-A-T observable signals (author via meta / schema / `rel=author` / byline,
  credentials or expert review — **required on YMYL pages, auto-detected**, publish /
  updated dates, staleness with `--as-of`, statistics without an outbound source,
  first-hand markers, About/Contact), structure (H1, heading skips, H2 on long pages),
  readability (sentence length, long sentences, walls of text, Flesch), depth floors per
  page type (article / product / local / home / category), keyword placement + stuffing,
  in-content internal links (nav/footer excluded) + generic anchors, and the
  scaled-content tells — **leaked template placeholders (critical)**, filler phrasing,
  duplicated sentences — plus passage citability via `geo_check`. Never labeled
  "AI-written"; never presented as Google's E-E-A-T score. `--url` fetches through the
  shared SSRF guard.
- `seo-page` now runs `tech_audit.py` + `content_audit.py` (two scores); its agent moves
  from WebFetch to the bundled SSRF-guarded fetchers (least privilege preserved).
  `seo-content` runs the audit, then judges what a script can't (claim accuracy,
  relevance of credentials, intent fit). Agent contracts report the real score.
- New `references/seo-content/content-rubric.md`; golden example
  `references/examples/seo-content/` (a YMYL article, 13/100, pinned).
- Gates: smoke 38/38, 575 unit tests (+16 in `tests/test_content_audit.py`),
  verify_release 56/56.

## v1.4.0 — 2026-09-25 — AI-search visibility depth (loop cycle 4 of 10)

Access → coverage → extractability: the three things that decide whether an AI answer
surface cites a page, each now measured.
- **New `scripts/seo/llms_txt.py`** — generate (`--generate site.json`, or
  `--from-urls` grouping by path segment) and validate llms.txt against the public
  proposal's structure (one H1 first, blockquote summary, H2 link lists, absolute
  URLs, duplicates, empty sections, size) with a 0-100 score. `geo_check.py` now scores
  the llms_txt category from this structural validation (invalid → capped at 60)
  instead of "has a `#`", and accepts `--llms FILE` offline.
- **Query fan-out coverage** — `geo_check.py --questions subqs.txt` finds the best
  passage per AI Mode sub-question and reports covered / missing terms (a stated
  lexical proxy; covered rows also say whether the answering passage is citable).
- **seo-drift rule D15** — `drift_baseline.py` / `drift_compare.py --robots` snapshot the
  shared AI-crawler verdict; a deploy that blocks AI-search crawlers or a search engine
  is **critical**, a partial block **high**, a training-only change advisory.
- New `references/seo-geo/ai-surfaces-2026.md` (per-surface playbook: AI Overviews,
  AI Mode, ChatGPT search, Perplexity, Claude, Copilot; fan-out method; honest AI
  visibility measurement). seo-geo gains the fan-out and llms.txt steps.
- Gates: smoke 38/38 (new llms_txt generate→validate), 559 unit tests (+16 in
  `tests/test_ai_visibility.py`), verify_release 56/56.

## v1.3.0 — 2026-09-25 — seo-schema promoted to Core (loop cycle 3 of 10)

`seo-schema` becomes a 3-layer Core skill (**16 Core · 26 Lite · 3 routing**).
- **`schema_gen.py` rewritten**: `@graph` flattening (wrapper `@context` inherited),
  nested-value validation (Product → Offer → OfferShippingDetails /
  MerchantReturnPolicy, ratings, reviews — `itemReviewed` implied when nested),
  **one-of requirement groups** (Product needs offers/review/aggregateRating), value
  rules (ISO 8601 dates, `dateModified ≥ datePublished`, absolute URLs, plain-number
  price, ISO 4217 currency, schema.org availability/condition enums, rating bounds,
  breadcrumb 1..N order), subtype inheritance (BlogPosting → Article, 40+ LocalBusiness
  subtypes), and a deterministic 0-100 score over `{type, severity, property, finding,
  fix}` issues.
- **New modes:** `--html` (extract + validate every ld+json block), `--graph` /
  `--graph-check` (cross-page `@id` entity graph: dangling refs, conflicting types,
  split Organization, missing hubs), `--site` (linked Organization → WebSite → WebPage →
  BreadcrumbList starter, self-validated). The agent's advertised `--graph-check` now
  actually exists — previously the doc promised a mode the script did not have.
- **Type coverage for 2026:** ProductGroup, MerchantReturnPolicy (org-level),
  OfferShippingDetails, AggregateOffer, ProfilePage, DiscussionForumPosting, QAPage,
  Recipe, JobPosting, SoftwareApplication, ImageObject, ItemList, Dataset (Dataset
  Search only); retired displays flagged info (FAQ 2026-05-07, HowTo, Course Info,
  Claim Review, Estimated Salary, Special Announcement, Vehicle Listing, practice
  problems).
- New `references/seo-schema/entity-graph.md`; schema catalog extended; new golden
  example `references/examples/seo-schema/` (validation 68/100, graph 90/100 — pinned).
- Gates: smoke 37/37, 543 unit tests (+19 in `tests/test_schema_gen.py`),
  verify_release 56/56.

## v1.2.0 — 2026-09-25 — seo-technical promoted to Core (loop cycle 2 of 10)

`seo-technical` becomes a real 3-layer Core skill (**15 Core · 27 Lite · 3 routing**).
- **`tech_audit.py` rewritten on `html.parser`** into a 10-dimension audit where every
  finding is a `{dimension, severity, finding, fix}` record, plus a deterministic
  **lab score** (100 − 25/critical − 10/high − 4/medium over observed signals only; field
  CWV stays `needs_tier1`). The `seo-technical` agent now returns that score instead of
  `null`, so the audit orchestrator can weight it.
- New checks: `X-Robots-Tag` / `googlebot` noindex, noindex+canonical conflict,
  nosnippet (AI Overview opt-out), multiple / relative / cross-host canonicals,
  **Googlebot's 2 MB uncompressed index limit**, doctype, charset, hreflang x-default,
  zoom-disabled viewport, JSON-LD parse errors + retired rich-result types (from
  `schema_gen.SPEC`), render-blocking head scripts, lazy-loaded LCP image, missing
  image dimensions (CLS), oversized inline JSON, client-rendered shell and JS-only
  links, Open Graph completeness, URL structure (case, params, session ids), redirect
  hops.
- **Bug fix:** a plain `<a href="http://…">` was reported as HIGH mixed content; only
  `http://` sub-resources are mixed content now (links are info).
- New `references/seo-technical/check-catalog.md` (checks, severity rationale, score
  formula, worked example); richer golden example (scores 64/100, pinned by test).
- Gates: smoke 37/37, 524 unit tests (+24 in `tests/test_tech_audit.py`),
  verify_release 56/56.

## v1.1.0 — 2026-09-25 — 2026 search currency (loop cycle 1 of 10)

First cycle of the "gold standard" pass: make every SEO fact current as of
September 2026 and give AI-crawler policy one source of truth.
- **New `scripts/seo/ai_crawlers.py`** — the one AI-crawler registry (four classes:
  search engine / AI search / user-triggered / training, with core flags) plus an
  **RFC 9309** robots.txt evaluator (group merge, specific-over-`*`, longest match,
  Allow wins ties, `*`/`$` wildcards) and a policy generator
  (`--generate citable-no-training`). `geo_check.py` and `tech_audit.py` now import
  it instead of carrying two diverging bot lists.
- **New verdict `search-engine-blocked`** (critical): a blocked Googlebot/Bingbot also
  removes AI Overviews / AI Mode / Copilot visibility; the GEO scorecard zeroes crawler
  access for it. User-triggered fetchers (ChatGPT-User, Claude-User, Perplexity-User)
  are judged as their own class; the Google-Extended scope note is emitted when it is
  blocked (it does not control AI Overviews).
- **New `references/shared/search-landscape-2026.md`** — dated fact sheet (AI Mode,
  2 MB Googlebot index limit, FAQ rich-result end on 2026-05-07, HowTo / sitelinks
  search box / 2025-retired features, spam policies incl. the August 2026 spam update,
  crawler classes, llms.txt confidence), cited by seo-audit / seo-technical / seo-geo.
- Fixes: "First Input Paint" → First Input *Delay* in `cwv-thresholds.md`; the schema
  catalog and `schema_gen.py` no longer promise a sitelinks search box; `HowTo` is now
  flagged as a retired rich result; SHIPPING's stale "13 CLI tools" list replaced with
  the real per-folder script inventory.
- Gates: smoke 37/37 (new ai_crawlers generate→judge round-trip), 500 unit tests
  (+22 in `tests/test_ai_crawlers.py`), verify_release 56/56.

## v1.0.4 — 2026-07-05 — open contribution workflow

Community contributions are now first-class (no code, skill, or gate change):
- `CONTRIBUTING.md` documents the full fork -> branch -> run-the-gates -> pull-request flow.
- Added a README "Contributing" section, a PR template, and bug / skill-idea issue
  templates under `.github/`.

## v1.0.3 — 2026-07-05 — acknowledgements

Added an "Acknowledgements & inspiration" note to NOTICE.md crediting the Skool
community whose ideas sparked the project's direction. No code, skill, or gate change;
no community material is bundled or redistributed.

## v1.0.2 — 2026-07-05 — README banner

Added a header banner image (`assets/banner.png`) at the top of the README. No code,
skill, or gate change.

## v1.0.1 — 2026-07-04 — docs clarity pass

README + marketplace-description polish only — no code or skill-behavior change (gates
unchanged: smoke 36/36, 477 unit tests, verify_release 56/56):
- Dropped the originality/clean-room marketing from the README and the plugin
  description; kept the MIT license note. The from-scratch authoring discipline and the
  PROVENANCE ledger are unchanged internally.
- Reframed "Why this plugin exists" — web design and SEO work hand-in-hand when building
  a site rather than being literally one workflow; clarified that "QA" is the
  pre-delivery quality-assurance gate (not Q&A) and why it sits late in the loop.
- Added a full 45-skill catalog with a one-line definition each; Core skills marked.
- Glossed "stdlib" as standard-library-only Python (nothing to pip install).

## v1.0.0 — 2026-07-04 — v1 "Deep Core"

The first deep release: a real parallel-dispatch SEO audit, deep original flagships,
the design ranker (the moat, revertible), and a clean-room governance/CI spine — built
in gated waves (W0–W5) on the `enrichment/v1-deep-core` branch and shipped as one
version. **45 Stable = 14 Core + 28 Lite + 3 routing**, and the breakdown is CI-verified
(C10) to partition the skills on disk exactly, so the count claim is mechanically
un-fakeable. Every wave is gate-green (smoke 36/36 + unittest + verify_release); W0–W3b
were additionally Codex-gated, **W3c–W5 gate on the automated suite at the owner's
direction** (external Codex/Gemini review deferred this pass).

### W0 — governance spine + clean-room CI guard
- ENGINE-CONTRACTS sections 11–16 (agents, per-skill references, templates/prompts,
  hooks spec-only, connector/SSRF, free-path-mandatory) + the DAG-spans-agents
  amendment + the optional `## Capability routing` section in canonical order.
- CAPABILITY-TIERS capability→tier map + machine-parseable routing-block spec;
  `references/shared/{cwv,wcag,schema,eeat,anti-slop}.md`; clean-room `AGENTS.md`;
  NOTICE Common Crawl Terms-of-Use attribution.
- Clean-room CI guard: `verify_release.py` 23 → 37 checks (third-party names/markers/
  source-headers, sync/lock, per-class provenance, cited-reference resolution, the
  named handoffs, count-band, stdlib-only with dynamic-import detection); a stdlib
  `unittest` suite + a CI unittest job; `csv_to_report` redacts contact PII by default.

### W1a — free-first script backbone
- `net_safety.py` shared SSRF guard (`validate_url` + IP-pinned `safe_open` closing
  DNS-rebinding TOCTOU), `page_fetch.py`, `site_map.py`, `cost_guard.py` (fail-open),
  the audit-math trio (`business_type`/`crawl_inventory`/`audit_aggregate`), a
  `capability_probe.py` env-var extension; existing fetchers retrofitted through the
  shared guard.

### W1a — design-engine ranker (the moat, behind a revert flag)
- `match.py`: weighted per-corpus IDF + field weights + length-norm + difflib fuzzy +
  confidence-floor/tie-margin honesty replaces raw token-overlap, sharpening palette
  and typography toward each product's own mood (generic high-frequency tokens no
  longer dominate); style and pattern are unchanged. `DPS_RANKER=legacy` reverts
  byte-for-byte for one release; `gen_palettes` byte-reproducibility and the
  explicit-style-override regression are preserved.

### W2 — the agent scaffold (template + one proof leaf)
- `agents/_TEMPLATE.md` authoring scaffold + the `seo-technical` proof agent; the
  `## Capability routing` + machine-parseable `## Output contract` shape every leaf fills.
- verify_release gains C3 (agent well-formedness; name/file/sibling parity; dispatch-
  shape do-not-match), C5 (least-privilege frontmatter — a fetch-only agent may not also
  hold Bash), and C4 (every routing-block skill ships a real on-disk Tier-2 exercised by
  a golden example); `test_agents.py`, `test_tier2_present.py`.

### W3 — flagship depth (SEO + design differentiators)
- **SEO (W3a):** `seo-cluster` (SERP-overlap `serp_cluster.py` + from-scratch
  `cluster-map.html`), `seo-drift` (SQLite baseline/compare/history + severity engine),
  `seo-local-unified` (`nap_check.py` + `geogrid.py` SoLV over free Nominatim), `seo-geo`
  (weighted GEO scorecard + passage citability); leaf scripts RED-first.
- **Design (W3b):** `match.py` wired under `design_system.py`; `gen_charts.py` +
  `chart-types.csv`; `a11y_static.py`; `card/muted/border/ring/destructive` palette slots
  (still byte-reproducible); per-skill references (ranking, anti-slop, chart-selection,
  competitor-rubric, white-space-method, visual-qa, structural-checks).
- **seo-strategy (W3c):** an original six-stage evidence loop (Baseline / Diagnose /
  Cluster / Prioritize / Produce / Verify) derived from the plugin's own engine
  subsystems — not any external four-stage framework — plus five vertical templates from
  `business_type.py`. Authored source-closed; the PROVENANCE method note records that
  the third-party framework's source text was not opened during authoring. No
  `prompts.lock`, no sync script, no attribution header.

### W4 — orchestrator wiring (real parallel fan-out)
- **`seo-audit`** now dispatches real Agent-tool sub-agents in parallel — 5 always-on
  (`seo-page` / `seo-technical` / `seo-schema` / `seo-sitemap` / `seo-image-audit`) + 6
  conditional (`seo-content` / `seo-geo` / `seo-local-unified` / `seo-ecommerce` /
  `seo-google` / `seo-backlinks`) dispatched-leaf agents — fanned in through
  `audit_aggregate.py`'s re-normalized health score. New references
  `references/seo-audit/{dispatch-matrix,scoring-weights}.md`; the stale
  30/30/15/10/15 prose is reconciled to the real weight table.
- **`parallel-build`** fans out N build sub-agents behind the shared-token barrier →
  optional N×`design-visual-qa` agents for per-variant comparison; **`qa-gate`** phase 3
  → `design-accessibility` agent, phase 7 → `seo-page` agent, phase 4 → `seo-google`
  (cost-guard fail-open before any paid call).
- 12 dispatched-leaf agents authored just-in-time — each wraps its sibling skill with no
  forked logic and least-privilege tools. verify_release gains C3 dispatch↔disk parity
  (every dispatched specialist has an agent; every agent is wired to an orchestrator);
  `test_dag.py` proves the skill+agent graph is acyclic. The dispatch split is **5 + 6**
  (derived from our own specialists, not the source's 8 + 7).
- Truth-in-advertising: the `backlinks` Tier-2 in `capability_probe.py` and
  CAPABILITY-TIERS now names the real WebSearch mention/linking-domain free path rather
  than the unshipped `backlinks_discover.py` (the Common-Crawl web-graph scripts are
  deferred to v1.1).

### W5 — status-truth & release certification
- **Depth tiers (Core / Lite / routing)** added to `SHIPPING.md` as a machine-readable
  partition + narrative; the promotion checklist gains Core criteria (orchestrator
  parity C3, free-path proof C4, depth proof C1/C5).
- verify_release gains **C10** — the three tiers partition the 45 skills on disk exactly
  (no skill missing / invented / double-counted) and the `14 Core / 28 Lite / 3 routing`
  breakdown triangulates across SHIPPING / README / plugin.json — and **C2** — no trigger
  phrase is claimed by two skills (the `AI visibility` collision between `seo-dataforseo`
  and `seo-geo` is disambiguated to `AI visibility check` vs `AI visibility optimization`).
- Version bumped **0.4.3 → 1.0.0** across plugin.json + marketplace.json; the wave log is
  consolidated into the single v1.0.0 release entry above.

## v0.4.3 — 2026-06-28 — skill-description cleanup + correctness pass

A plugin-wide professionalization pass driven by a 51-agent audit of all 45 skills
against the engine contracts, clean-room rules, and doc consistency. Codex-gated
(round 1 DO-NOT-SHIP → round 3 SHIP); gates green (smoke 36/36, release 23/23).

### Descriptions + triggers
- Audited and tightened skill `description:` frontmatter across the suite for clarity,
  accuracy, and free-first framing — each now claims only what its body delivers and is
  YAML-safe (no colon-space in the scalar).
- De-duplicated colliding trigger phrases: `baseline` → `SEO baseline` (seo-drift, vs
  design-visual-qa's visual baseline); dropped bare `compare competitors` /
  `competitor comparison` from seo-competitor-pages; `AI visibility check` →
  `AI-visibility data` (seo-dataforseo); `sanity check this` → `sanity-check what you
  wrote` (route-codex-review).

### Correctness + contracts
- Fixed bare `scripts/...` invocations that resolve to the user's CWD once installed —
  `seo-firecrawl`, `seo-google`, `seo-image-gen` now call bundled scripts via
  `${CLAUDE_PLUGIN_ROOT}`.
- Broke two dependency cycles (`copywriting`↔`design-cro`,
  `seo-cluster`↔`seo-content-brief`) by moving the back-edge to a Notes "Related skills"
  line, preserving the one-directional orchestrator→specialist DAG.
- Truth-in-advertising: `seo-sitemap` "rejects" → "flags sampled" URLs;
  `client-outreach` "compliant list" → "compliance-checklist fields"; `seo-strategy`
  drops the "original methodology" framing for the Evidence Loop.

### Docs + metadata
- README enumerates all 45 skills (added `blast-prompt`); `references/README` indexes
  `CAPABILITY-TIERS.md` and corrects the `html-extract` output path; `extensions/README`
  DataForSEO "used by" list corrected to all 10 consuming skills.
- Unified and front-loaded the `plugin.json` / `marketplace.json` description ("45 stable
  skills" first) and broadened keywords with SEO terms.

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
- Renamed a third-party SEO methodology to an original **Evidence Loop**.

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
