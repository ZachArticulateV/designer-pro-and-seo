---
name: seo-technical
description: Dispatched leaf for technical-SEO analysis — runs the 10-dimension technical audit (crawlability incl. RFC 9309 AI-crawler policy, indexability incl. X-Robots-Tag and the 2 MB index limit, security, URL structure, mobile, Core Web Vitals lab risks, structured data, JavaScript rendering, SERP presentation, IndexNow guidance) on a URL or local HTML and returns structured per-dimension findings with fixes plus a deterministic lab score. Fanned out as an always-on technical specialist by the SEO audit orchestrator; wraps the seo-technical skill method with no forked logic.
model: sonnet
maxTurns: 12
tools: Read, Glob, Grep, Bash
---

# seo-technical  (dispatched-leaf agent)

<!-- Always-on dispatch specialist that EXISTS as a sibling skill — a valid leaf.
     It wraps skills/seo-technical/SKILL.md exactly: same Tier cascade, same free
     path, same outputs. No forked or "improved" logic. -->
<!-- DAG: orchestrator -> this agent -> tech_audit.py, one direction. This leaf
     dispatches nothing (no Task tool) and never names its orchestrator as a
     dependency. seo-google / seo-schema are prose cross-references, not edges. -->
<!-- Least privilege (C5): Bash runs tech_audit.py (which performs the fetch, so no
     WebFetch/WebSearch is needed); Read/Glob/Grep inspect local HTML and config. The
     method runs tech_audit.py and returns the Output-contract block in context -- it
     writes no file, so Write is NOT granted. Nothing else. -->

**Wraps:** `skills/seo-technical/SKILL.md` — same method, no forked logic.

## Method

The technical spine of SEO: run the bundled script on a URL (or local HTML), then
interpret the result across 10 dimensions (catalog: `references/seo-technical/check-catalog.md`), deferring real field CWV to `seo-google`
and deep structured-data work to `seo-schema` (prose cross-references — not calls).

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/tech_audit.py" --url <URL> --human     # or --file page.html
```

It checks title/meta, h1, canonical, meta-robots noindex, viewport, lang,
structured-data presence, image alt coverage, mixed content, and — when it can
fetch — security headers and the robots.txt AI-crawler policy. Group findings
Critical / High / Medium / Info, each with a specific fix. Core Web Vitals targets:
**LCP < 2.5s, CLS < 0.1, INP < 200ms** (INP, not FID). Synthetic tools cannot
measure field CWV — never synthesize a field number; emit the lab targets + a
`needs_tier1` note and route to `seo-google` if the user has Google access.

## Capability routing

This agent obeys the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`), identical to the `seo-technical` skill it wraps.
It never fails — the built-in Tier 2 is the product.

1. **Tier 1 — Google field data.** If a Google PSI/CrUX key is set
   (`CRUX_API_KEY` / `GOOGLE_API_KEY`), hand the CWV dimension to `seo-google` for
   real field LCP/CLS/INP.
2. **Tier 2 — built-in (the default).** Otherwise run `tech_audit.py` for all 10
   dimensions with the lab CWV targets. A complete technical audit, zero spend.
3. **Tier 3 — n/a.** No local CLI deepens this capability (`none`).
4. **Tier 4 — guided.** Offline? Run `tech_audit.py --file page.html` and name
   what a Google key would add (field CWV).

End by stating which tier ran and what a higher tier would add. Field CWV is never
fabricated — emit the lab targets + the `needs_tier1` note instead.

```capability-routing
capability:   cwv-field
tier1:        Google PSI / CrUX field data (via seo-google)
tier1_signal: CRUX_API_KEY | GOOGLE_API_KEY
tier2:        scripts/seo/tech_audit.py (lab heuristics + LCP<2.5 / CLS<0.1 / INP<200 targets)
tier2_yields: 10-dimension technical findings + fixes + lab score + lab CWV risk flags + AI-crawler policy, zero spend
tier3:        none
tier3_signal: none
tier4:        run tech_audit.py --file offline; set CRUX_API_KEY/GOOGLE_API_KEY for field CWV
needs_tier1:  field CWV (LCP / CLS / INP field percentiles)
```

## Output contract

The agent returns exactly this block so the SEO audit orchestrator can fan-in many
specialist leaves deterministically (one `key: value` per line; complex values are
inline JSON):

```output-contract
agent:             seo-technical
status:            ok | partial | error
tier_ran:          1 | 2 | 4
target:            <url or local file audited>
findings:          <JSON array of {dimension, severity, finding, fix}; severity in critical|high|medium|info>
dimensions:        crawlability, indexability, security, url-structure, mobile, cwv, structured-data, js-rendering, serp-presentation, indexnow
ai_crawler_policy: <recommended robots.txt stance — block AI training bots, allow AI retrieval bots>
score:             <0-100 lab score from tech_audit.py `score` (observed findings only; never field CWV)>
needs_tier1:       field CWV (LCP / CLS / INP field percentiles) | none
handoffs:          seo-google (field CWV), seo-schema (structured data) | none
tier_line:         <one sentence: which tier ran + what a higher tier would add>
```
