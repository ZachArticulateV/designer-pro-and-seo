---
name: design-research
description: Run a competitive research pass on a site and its top competitors, producing a structured competitive-intelligence report (brand snapshot, competitor scoring, white-space analysis, keyword landscape) that informs the rest of the design and SEO workflow. Uses the Firecrawl MCP for deep multi-page scraping when connected; otherwise built-in web fetch/search + html-extract. Trigger when the user says "competitive research", "competitor analysis", "research the niche", "what are competitors doing", "give me a competitive report", or is starting a new engagement.
---

# design-research

**Family:** design
**Status:** Stable

## Purpose

The research front-end of an engagement. Given a target domain and a niche, it
captures the target's positioning, identifies top competitors, scores each on key
dimensions, surfaces the white space no one is filling, and produces a markdown or
interactive-HTML report that feeds `design-system-gen`, `design-dimensions`,
`blast-prompt`, and the SEO skills. It is **tool-aware**: with the Firecrawl MCP it
does deep multi-page scraping; without it, built-in web fetch/search + `html-extract`
still produce a real competitive read.

## Triggers

- "competitive research" / "competitor analysis"
- "research the niche" / "niche research"
- "what are competitors doing"
- "give me a competitive report"
- "client research" / "engagement research"

## Inputs

- Target domain
- Industry / vertical
- Geographic scope (local / national / global)
- Number of competitors (default 5)
- Output format: markdown | interactive HTML | both

## Steps

1. **Detect tooling.** Check whether the Firecrawl MCP is connected
   (`scripts/workflow/capability_probe.py` reports `FIRECRAWL_API_KEY`).
2. **Capture the target.** Tier 1: Firecrawl-scrape the site for voice, services,
   positioning. Tier 2: WebFetch the key pages + `html-extract` for structure/tokens.
3. **Identify competitors.** Use WebSearch on the niche + the target's core terms to
   assemble a competitor set (default 5); let the user confirm/adjust.
4. **Scan each competitor.** Same tier path as step 2, one pass per competitor.
5. **Score each** on: brand strength, content depth, design quality, trust signals,
   SEO baseline, conversion patterns. Use a consistent rubric so scores compare.
6. **Find the white space** — dimensions where every competitor is weak.
7. **Keyword landscape** — call `seo-cluster` if available; otherwise a WebSearch-based
   intent grouping.
8. **Compose the report** into the user's workspace (see Outputs).
9. **Report which tier ran** and what a full Firecrawl crawl would add.

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`):

1. **Tier 1 — Firecrawl MCP.** If connected, deep multi-page scraping of target +
   competitors.
2. **Tier 2 — built-in (default).** WebFetch + WebSearch + `html-extract` for a real
   competitive read from the key pages.
3. **Tier 4 — guided.** If a site is JS-rendered and Firecrawl isn't connected, work
   from the pages you can fetch and note what a full crawl would add.

Always state which tier ran and what Firecrawl would add.

## Outputs

Written into the user's project workspace:
- `research/01-target-brand.md` — brand/positioning extraction
- `research/02-competitor-analysis.md` — scored analysis + keyword landscape
- `research/03-build-brief.md` — synthesized build brief drawing from the above
- Optional: `competitive-analysis.html` — interactive scoring report

## Dependencies

- Optional (Tier 1): Firecrawl MCP (`extensions/firecrawl/`) — deep scraping; free
  path works without it
- Built-in (Tier 2): WebFetch; WebSearch; `html-extract`
- `seo-cluster` (optional — keyword landscape); `scripts/workflow/capability_probe.py`

## Notes

The output structure is a proven engagement shape, made repeatable here instead of
bespoke per project. Respect target sites' robots.txt and Terms of Service when
scraping (see `PRIVACY.md`); research artifacts stay in the user's workspace.
