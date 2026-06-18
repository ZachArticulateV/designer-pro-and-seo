---
name: seo-backlinks
description: Backlink profile analysis — referring domains, anchor distribution, toxic-link flags, competitor gap, link-building targets. Uses a connected link-data MCP (DataForSEO / Moz / Bing) for full metrics when present; otherwise builds a qualitative profile via web-search mention/linking-domain discovery (the free path is qualitative — exact counts, authority, and toxic-link confirmation need a connected provider). Trigger when the user says "backlinks", "link profile", "referring domains", "anchor text", "toxic links", "link gap", "link building", "disavow", "backlink audit".
---

# seo-backlinks

**Family:** seo
**Status:** Stable

## Purpose

Backlink intelligence on a free-to-premium ladder. **Tool-aware:** with a link-data
MCP connected (DataForSEO/Moz/Bing) it returns a full referring-domain profile with
metrics; without one, it assembles a *qualitative* profile from public signals
(Common Crawl web graph, Bing Webmaster) plus web-search mention discovery — rarer
than it sounds on the free tier, and a genuine differentiator.

## Triggers

- "backlinks" / "backlink audit"
- "link profile" / "referring domains"
- "anchor text"
- "toxic links" / "disavow"
- "link gap" / "competitor backlinks"
- "link building"

## Inputs

- Domain
- Optional competitor domains (for gap analysis)
- Tier preference (auto | built-in | premium)

## Steps

1. **Detect tooling.** Check whether a link-data MCP (DataForSEO/Moz/Bing) is exposed
   this session (`scripts/workflow/capability_probe.py` reports relevant keys).
2. **Premium path (Tier 1, if connected).** Pull the full profile via the connected
   MCP (referring domains, anchors, authority metrics); flag toxic links on
   conservative thresholds; compute competitor gap.
3. **Built-in path (Tier 2, always available).** Assemble a qualitative profile with
   WebSearch: discover brand/URL mentions and likely linking domains, and group them.
   If you have access to a public web-graph (Common Crawl / Bing Webmaster), fold it
   in — the plugin ships no such fetcher, so treat it as optional. Label the result
   qualitative: exact counts, authority, and confirmed toxicity need Tier 1.
4. **Synthesize.** Produce the inventory, an anchor-text read, conservatively-flagged
   toxic candidates (with the caveat that confirmation needs metrics), and a
   competitor-gap prospect list.
5. **Report which tier ran** and what a link-data MCP would add.

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`):

1. **Tier 1 — link-data MCP.** DataForSEO/Moz/Bing if connected → full metric profile.
2. **Tier 2 — built-in (default).** Common Crawl / Bing public signals + WebSearch
   mention discovery → a qualitative profile and prospect list.
3. **Tier 4 — guided.** If the user needs authoritative counts/scores and no MCP is
   connected, deliver the qualitative profile and name the setup to unlock metrics.

Always state which tier ran and what a link-data provider would add.

## Outputs

- Backlink inventory (metric-rich on Tier 1; qualitative on Tier 2)
- Anchor-text distribution read
- Toxic-link candidates with a disavow-file recommendation (conservative)
- Competitor gap with a link-building prospect list

## Dependencies

- Optional (Tier 1): a link-data MCP — `seo-dataforseo` (DataForSEO), or Moz/Bing —
  adds full metrics; free path works without it
- Built-in (Tier 2): WebSearch; public Common Crawl / Bing Webmaster signals
- `scripts/workflow/capability_probe.py`

## Notes

Toxic-link thresholds are conservative by default — better to under-flag than to
recommend disavowing a healthy link. Free-tier backlink intelligence is the
differentiator here.
