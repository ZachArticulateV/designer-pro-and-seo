---
name: seo-dataforseo
description: Premium SERP / keyword / backlink / AI-visibility data via the DataForSEO MCP when connected (volume, difficulty, multi-engine SERP, image SERP, LLM-mention tracking); otherwise a qualitative SERP and keyword read from built-in web search, clearly labeled lower-fidelity. Trigger when the user says "dataforseo", "live SERP", "keyword volume", "keyword difficulty", "backlink data", "competitor data", "AI visibility check", "LLM mentions", "image SERP", "real search data".
---

# seo-dataforseo

**Family:** seo
**Status:** Stable

## Purpose

The premium data hub for the SEO family. **Tool-aware:** with the DataForSEO MCP
connected it returns hard metrics (search volume, keyword difficulty, multi-engine
and image SERP, referring domains, LLM-mention tracking); without it, it gives a
qualitative SERP/keyword read from built-in web search so you still get a current
ranking snapshot and competitor URLs — clearly labeled as lower-fidelity, with the
exact metrics that require the MCP named.

## Triggers

- "dataforseo"
- "live SERP" / "real search data"
- "keyword volume" / "keyword difficulty" / "keyword research"
- "backlink data" / "competitor data"
- "AI visibility" / "LLM mentions" / "ChatGPT mentions"
- "image SERP" / "google images rankings"

## Inputs

- Query type (SERP | keyword | backlinks | AI-visibility)
- Keyword(s) / domain / parameters per call

## Steps

1. **Detect tooling.** Check whether the DataForSEO MCP is exposed this session
   (`scripts/workflow/capability_probe.py` reports `DATAFORSEO_*`).
2. **Premium path (Tier 1, if connected).** Call the DataForSEO MCP for the request;
   normalize into a compact table (volume/difficulty/positions/referring domains as
   applicable).
3. **Built-in path (Tier 2, always available).** Use WebSearch to read the current
   SERP for the keyword(s): capture ranking URLs, titles, and apparent intent, and a
   competitor URL list. **Do not fabricate** volume, difficulty, or CPC — state that
   those require Tier 1.
4. **Report which tier ran** and which specific metrics DataForSEO would add.

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`):

1. **Tier 1 — DataForSEO MCP.** If connected, use it for volume, difficulty,
   multi-engine + image SERP, backlinks, and AI-visibility data.
2. **Tier 2 — built-in (default).** Otherwise a WebSearch SERP read: ranking URLs,
   titles, intent, competitor set. Qualitative — no volume/difficulty/CPC.
3. **Tier 4 — guided.** If the user needs hard metrics and the MCP isn't connected,
   deliver the qualitative read and name the setup (add the DataForSEO extension).

Always state which tier ran and which metrics need DataForSEO.

## Outputs

- The requested data as a compact table (hard metrics on Tier 1; a qualitative SERP
  snapshot + competitor URLs on Tier 2)
- An explicit "needs DataForSEO" list for any metric the free path can't measure

## Dependencies

- Optional (Tier 1): DataForSEO MCP (`extensions/dataforseo/`, paid) — adds the hard
  metrics; free path works without it
- Built-in (Tier 2): WebSearch
- `scripts/workflow/capability_probe.py`

## Notes

When connected, this is the data plumbing other skills draw on (`seo-backlinks`,
`seo-cluster`, `seo-ecommerce`, `seo-local-unified`, `seo-content-brief`,
`seo-sxo`). Each of those also has its own free path; none hard-fails without this.
