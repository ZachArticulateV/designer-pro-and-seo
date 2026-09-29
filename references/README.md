# references/

Deep knowledge that skills load **on demand**. Keeping it here keeps each `SKILL.md`
short: a skill names a file by exact path, and the release gate checks that every cited
path resolves. These files hold knowledge (rubrics, thresholds, code tables, worked
examples), not procedure. Procedure lives in the skill's `## Steps`.

## Start here

| File | What it is |
|---|---|
| `shared/search-landscape-2026.md` | **Dated fact sheet** of what is true in search right now: AI Overviews / AI Mode, the 2 MB index limit, retired rich results, crawler classes. Reviewed quarterly. |
| `ENGINE-CONTRACTS.md` | The interface spec every skill, script, agent and template follows |
| `CAPABILITY-TIERS.md` | The Tier 1→4 tool cascade: use a connector when present, otherwise the free path |
| `PROVENANCE.md` | The clean-room ledger: who authored every asset and from what public basis |
| `skill-section-template.md` | Copy-ready `SKILL.md` skeleton in the canonical section order |

## shared/: knowledge several skills cite

`search-landscape-2026.md`, `cwv-thresholds.md`, `schema-catalog.md`,
`eeat-criteria.md`, `wcag-contrast-rules.md`, `anti-slop-principles.md`

## Per-skill folders: the depth behind each Core skill

| Folder | Holds |
|---|---|
| `seo-technical/` | check catalog, severity ladder, lab-score formula |
| `seo-schema/` | `@id` conventions, value rules, entity-graph scoring |
| `seo-content/` | content rubric, page-type depth floors, YMYL bar |
| `seo-sitemap/` | S/G/L codes: validation, quality gates, link architecture |
| `seo-image-audit/` | image codes, byte/pixel budgets, format targets |
| `seo-geo/` + `geo-scorecard.md` | AI-surfaces playbook, fan-out method, GEO scoring |
| `seo-hreflang/`, `seo-ecommerce/` | cluster rules; merchant-listing and facet checks |
| `seo-audit/` | dispatch matrix (who runs when) and health-score weights |
| `seo-cluster/`, `seo-drift/`, `seo-local-unified/`, `seo-strategy/` | clustering method, drift rules D1–D15, SoLV + NAP, the evidence-led strategy prompts |
| `design-*/` | design-system ranking, build anti-slop, accessibility checks, CRO heuristics, motion rubric, visual-QA rubric, research rubric |

## examples/: golden outputs

One folder per Core skill with real inputs, the exact command, and the expected
result. Tests pin each one (see `examples/README.md`).

`DEEP-DIVE-ANALYSIS.md` is the archived pre-v1 roadmap, kept for provenance only.
