# scripts/

The plugin's engine room: **42 standard-library Python scripts** that skills call
instead of embedding logic in `SKILL.md` bodies. Nothing to `pip install`. Every
script runs as a CLI **and** imports as a library, prints JSON by default (`--human`
for ASCII), is deterministic for the same input, and exits non-zero with a JSON error
on bad input. Any script that fetches a URL goes through the one shared SSRF guard,
`workflow/net_safety.py`.

Skills invoke them as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<folder>/<script>.py"`.
From a clone, run them with bare `scripts/...` paths from the repo root.

## seo/: one engine per SEO specialist

| Script | What it does |
|---|---|
| `tech_audit.py` | 10-dimension technical audit with a fix per finding and a lab score |
| `content_audit.py` | E-E-A-T signals (YMYL-aware), structure, readability, depth, keywords, links, scaled-content tells |
| `schema_gen.py` | JSON-LD generate / validate (nested values), cross-page `@id` graph, site-graph starter |
| `sitemap_tools.py` | sitemap validate (lastmod honesty, extensions), quality gates, SSRF-guarded live sample, generate |
| `link_graph.py` | internal-link architecture: orphans, click depth, broken links, anchors |
| `image_audit.py` | alt quality, formats, srcset, LCP loading, CLS, real byte + pixel budgets |
| `geo_check.py` | passage citability, GEO scorecard, AI Mode fan-out coverage |
| `ai_crawlers.py` | the one AI-crawler registry + RFC 9309 robots evaluator + policy generator |
| `llms_txt.py` | llms.txt generate / validate |
| `hreflang_tools.py` | hreflang code rules, cross-page cluster audit, tag generation |
| `product_audit.py` | merchant-listing checks (markup vs visible page) + category facet / pagination hygiene |
| `site_map.py`, `crawl_inventory.py`, `page_fetch.py` | discovery: robots + sitemap recursion, URL bucketing, guarded fetch |
| `business_type.py` | business-type classifier that gates conditional specialists |
| `serp_cluster.py` | SERP-overlap keyword clustering + pillar selection |
| `geogrid.py`, `nap_check.py` | local SEO: share-of-local-voice grid math, NAP consistency |
| `drift_tools.py`, `drift_baseline.py`, `drift_compare.py`, `drift_history.py`, `drift_severity.py` | SEO drift: capture, SQLite baselines, rules D1–D15 |

## design/: design engine + design audits

| Script | What it does |
|---|---|
| `design_system.py`, `match.py` | CSV-backed design-system reasoning (`match.py` is the ranker library) |
| `gen_palettes.py`, `gen_charts.py` | WCAG-checked palettes; data-shape → chart recommendations |
| `render_page.py`, `tokens_emit.py` | accessible single-file page render; CSS / Tailwind / SCSS / Style-Dictionary tokens |
| `a11y_static.py` | structural WCAG 2.2 checks |
| `cro_audit.py` | conversion heuristics K1–K13, ranked by impact ÷ effort |
| `motion_audit.py` | motion a11y + performance M1–M9 (reduced motion, layout animation, focus) |

## workflow/: orchestrators and shared plumbing

| Script | What it does |
|---|---|
| `site_audit.py` | **one-command SEO health score** over a build (every engine → re-weighted score + one fix list) |
| `qa_gate.py` | **one-command pre-delivery gate**: PASS / CONDITIONAL / FAIL + the filled QA report |
| `audit_aggregate.py` | re-normalized health-score fan-in |
| `net_safety.py` | the shared SSRF guard (every fetch goes through it) |
| `cost_guard.py`, `capability_probe.py` | fail-open spend guard; tool / key detection for the tier cascade |
| `portable_html.py`, `csv_to_report.py` | single-file HTML porter; CSV profiler with PII redaction |

## Release gates (repo root of this folder)

- `smoke_test.py`: install verification (40 checks). Run it after cloning.
- `verify_release.py`: the release gate: docs and version consistency, provenance,
  clean-room hygiene, agent least-privilege, tier partition, and more.

Provenance for every script is recorded in `references/PROVENANCE.md`.
