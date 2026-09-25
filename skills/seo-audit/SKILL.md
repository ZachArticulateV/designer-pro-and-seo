---
name: seo-audit
description: Orchestrates a multi-specialist SEO audit — detects business type, dispatches the available specialist skills, and aggregates one weighted health score with a prioritized, deduped fix list. Crawls up to ~500 pages when seo-firecrawl is connected; otherwise audits the key URLs you provide and says so. Trigger when the user says "seo audit", "full site audit", "comprehensive seo review", "analyze my site for seo", "website health check", or "audit my site for seo".
---

# seo-audit

**Family:** seo
**Status:** Stable

## Purpose

The orchestrator and public face of the SEO family. Runs the available specialist
skills against your target, then aggregates their findings into one weighted health
score with a prioritized fix list — so the user gets a single answer, not eight
disconnected reports.

Scope note (honest): it audits the **URLs you provide** out of the box. Full-site
crawling (up to ~500 pages, business-type auto-detect at scale) activates when the
`seo-firecrawl` skill is installed; without it, point it at the key URLs.

## Triggers

- "seo audit" / "full site audit" / "comprehensive seo review"
- "analyze my site for SEO" / "website health check"
- "audit [domain]"

## Inputs

- A domain, a URL, or a small list of key URLs
- Optional: business-type override; specialist include/exclude

## Steps

1. **Scope.** Take the URL(s). If `seo-firecrawl` is available, crawl to discover
   pages; otherwise audit the provided URLs and say so. **For a local static build**,
   the whole free path is one command — every applicable engine, per-specialist
   scores, the re-normalized health score, a covered / not-covered list, and one fix
   list merged across pages:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/site_audit.py" --dir dist/ --base-url https://site.com --human
   ```
   Use it as the baseline, then dispatch the agents below for live URLs and for the
   judgement the engines can't make.
2. **Profile.** Infer business type (SaaS / e-commerce / local / publisher /
   agency) from the content to decide which conditional specialists apply.
3. **Dispatch the specialist agents in parallel** — real Agent-tool sub-agents, each
   a dispatched leaf under `agents/` (one-directional, no back-edges). The full roster
   and the dispatch conditions are in `references/seo-audit/dispatch-matrix.md`. Always
   fan out the five always-on agents:
   - `seo-page` — per-URL on-page review
   - `seo-technical` — technical dimensions (`tech_audit.py`)
   - `seo-schema` — structured-data validation
   - `seo-sitemap` — sitemap structure + gates
   - `seo-image-audit` — image SEO
   Then add the conditional agents the profile and connected tooling call for:
   `seo-content` (content depth / E-E-A-T) and `seo-geo` (AI-citability) by default,
   plus `seo-local-unified` for a local business or `seo-ecommerce` for a store; when
   their tools are connected, also `seo-google` (real CWV / rankings) and
   `seo-backlinks`. Each agent obeys the plugin's tier cascade and returns its
   machine-parseable `## Output contract` block for deterministic fan-in. Record which
   specialists ran and which were skipped (and why) rather than implying coverage you
   didn't run.
4. **Aggregate + score.** Collect each agent's Output-contract score and feed the
   per-specialist map to `scripts/workflow/audit_aggregate.py`, which computes one
   weighted health score (0–100) **re-normalized over the specialists that actually
   ran** — a skipped specialist is excluded from the denominator, never zeroed. The
   weight table (anchors `seo-technical` and `seo-page` at 20; `seo-content` 15; the
   mid band at 10; `seo-geo` 5) and the grade bands are in
   `references/seo-audit/scoring-weights.md`. Report the weighting used.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/audit_aggregate.py" --file scores.json --human
   ```
5. **Prioritize.** Merge findings into one list: Critical → High → Medium → Low,
   deduped, each with the owning specialist and a specific fix.
6. **Render** the health score, the prioritized fix list, and per-specialist
   appendices. State explicitly which specialists ran and which were skipped.

## Outputs

- Weighted health score (0–100) with the weighting shown
- One prioritized, deduped fix list (Critical/High/Medium/Low)
- Per-specialist detail appendices + an explicit "covered / not covered" list

## Dependencies

- Core specialists (always): `seo-page`, `seo-technical`, `seo-schema`, `seo-sitemap`,
  `seo-image-audit` — each dispatched as its `agents/<name>.md` leaf
- Conditional specialists (by business type / connected tooling): `seo-content`,
  `seo-geo`, `seo-local-unified`, `seo-ecommerce`, `seo-google`, `seo-backlinks`
- `references/seo-audit/dispatch-matrix.md` (required) — the always/conditional roster
  + dispatch conditions the Steps fan out over
- `references/seo-audit/scoring-weights.md` (required) — the health-score weight table
  + re-normalization + grade bands
- `scripts/workflow/audit_aggregate.py` (required) — re-normalized health-score fan-in
- `scripts/workflow/site_audit.py` (required) — the local one-command engine run + fan-in
- `scripts/seo/business_type.py` (required) — business-type classification for
  conditional dispatch
- Optional: `seo-firecrawl` (full-site crawl)

## Notes

Current-state facts every specialist relies on (AI Overviews / AI Mode sourcing,
retired rich results, crawl limits, spam policies) are dated in
`references/shared/search-landscape-2026.md`; cite it rather than restating a fact.

Most SEO requests should land here first; it routes to specialists. It dispatches
real Agent-tool sub-agents in parallel (`agents/`), one per specialist leaf, and never
claims coverage it didn't run — the "covered / not covered" list plus the
re-normalized denominator keep the health score honest. Adding a new specialist agent
auto-joins this socket (see `references/seo-audit/dispatch-matrix.md`).
