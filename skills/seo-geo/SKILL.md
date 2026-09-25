---
name: seo-geo
description: Optimize content to be cited inline by AI answer engines — AI Overviews, ChatGPT, Perplexity, and Bing Copilot. Scores passage-level citability, generates llms.txt, audits AI-crawler access, and recommends structured-data and brand-mention signals. Uses DataForSEO for LLM-mention tracking when connected; otherwise scores citability and gives on-page guidance without live mention data. Trigger when the user says "AI Overviews", "GEO", "generative engine optimization", "AI search optimization", "Perplexity citations", "ChatGPT search", "AI visibility optimization", or "llms.txt".
---

# seo-geo

**Family:** seo
**Status:** Stable

## Purpose

Optimize for AI-powered search, where the win condition is being **cited inline by
the AI answer**, not ranking #1. That requires different content patterns: passages
that make specific, verifiable, standalone claims; discoverability via llms.txt and
AI-crawler access; and structured data (a top-5 GEO citation factor in the GEO
study, Aggarwal et al., KDD 2024).

## Triggers

- "ai overviews" / "SGE" / "GEO" / "generative engine optimization"
- "AI search" / "LLM optimization" / "AI visibility optimization" / "ai citations"
- "perplexity" / "chatgpt search" / "bing copilot" / "llms.txt"

## Inputs

- A page URL and/or its content (file)
- An optional `robots.txt` (file or live) for the AI-crawler-policy verdict
- Target platforms (AI Overviews / Perplexity / ChatGPT / all)

## Steps

1. **Run the GEO checker (with the weighted scorecard):**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/geo_check.py" --content page.html \
     --robots robots.txt --scorecard --human
   ```
   It scores each passage's citability (sourced + self-contained + answer-first →
   0-100), counts structured-data blocks, reads the robots AI-crawler policy, and
   rolls those signals into a **weighted 0-100 GEO score** with a per-category
   breakdown (re-normalized over whatever signals are present, so a content-only
   offline run still scores). Add `--url https://site.com` to also check `/llms.txt`
   and fetch live robots. See `references/geo-scorecard.md` for the weight rationale,
   the passage rubric, and the crawler-verdict semantics.
2. **Passage citability** — rewrite the weak passages it lists so each leads with one
   specific, sourced claim (number/date/named source) that survives extraction.
3. **llms.txt** — if absent, create a Markdown `/llms.txt` summarizing the site's
   key pages for LLMs.
4. **AI-crawler access** — read the checker's crawler-policy **verdict**
   (`citable-training-blocked` is best practice; `retrieval-blocked` is the
   anti-pattern). Ensure retrieval bots (OAI-SearchBot, PerplexityBot,
   Claude-SearchBot) are allowed so the site stays citable, even if training
   crawlers are blocked.
5. **Structured data** — add Article/Organization/Breadcrumb schema via `seo-schema`.
6. **Brand mentions** — recommend earning mentions on sources LLMs trust; if the
   DataForSEO extension is present, pull LLM-mention tracking, else note it.
7. **Render** platform-specific action items (AI Overviews favors structured,
   sourced answers; Perplexity favors fresh, citation-dense pages).

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`) and always returns a citability report:

1. **Tier 1 — DataForSEO MCP.** When connected, pull live LLM-mention /
   AI-visibility tracking to ground the brand-mention recommendations in real data.
2. **Tier 2 — built-in (the default).** Otherwise `geo_check.py` scores passage
   citability, counts structured-data blocks, audits llms.txt + the AI-crawler
   policy, and emits a **weighted 0-100 GEO scorecard** entirely offline
   (`--content` / `--robots` / `--scorecard` / `--no-network`) — the free, on-page
   GEO path is the product.
3. **Tier 4 — guided.** If no mention data is available, deliver the citability
   score + on-page fixes and name DataForSEO as the way to add hard mention tracking.

```capability-routing
capability:   geo-citability
tier1:        DataForSEO MCP (LLM-mention / AI-visibility tracking)
tier1_signal: DATAFORSEO_USERNAME | DATAFORSEO_PASSWORD
tier2:        geo_check.py (weighted GEO scorecard + passage citability + structured-data count + llms.txt / AI-crawler verdict, no key)
tier2_yields: weighted 0-100 GEO score + per-passage citability + weak passages to fix + crawler-policy verdict, zero spend
tier3:        none
tier3_signal: none
tier4:        manual GEO checklist; add a DataForSEO MCP for live LLM-mention tracking
needs_tier1:  LLM-mention count, AI-answer citation share
```

Always end by stating which tier ran and what mention data a higher tier would add.

## Outputs

| Output | What it contains | Format | Quality bar (how it is scored) |
|---|---|---|---|
| GEO scorecard | weighted 0-100 score + per-category breakdown (passage citability 45 / crawler access 25 / structured data 20 / llms.txt 10), re-normalized over available signals | JSON (`geo_score`) + `--human` ASCII | deterministic; names every excluded category; never weights a signal it did not observe |
| Passage citability | per-passage 0-100 (sourced + self-contained + answer-first) + the weak passages to fix | JSON (`citability`) + ASCII | each weak passage carries a specific, actionable reason; `citable` stays sourced+standalone+≤120w |
| AI-crawler verdict | retrieval-vs-training stance + verdict (`citable-training-blocked` … `retrieval-blocked`) + recommendation | JSON (`ai_crawler_policy`) | judges against the best practice (stay retrievable, opt out of training); reads real robots grouping |
| Structured-data + brand-mention items | per-platform action items; llms.txt status | prose / Info group | every item carries a concrete fix |
| Tier line | which tier ran + what a higher tier would add | one sentence | states the tier honestly; LLM-mention count ships as a `needs_tier1` proxy, never a fabricated number |

Filed to: the user's project workspace. LLM-mention count and AI-answer citation
share are never fabricated — they ship as a labeled `needs_tier1` list (add a
DataForSEO / AI-visibility MCP).

## Error Handling

| Condition | Detection | Behavior (degrade, never fail) | User-facing message |
|---|---|---|---|
| DataForSEO MCP absent | the MCP is not exposed / errors | run `geo_check.py` for the full offline scorecard | "Ran Tier 2 (geo_check.py). Add a DataForSEO MCP for live LLM-mention tracking." |
| No network / offline | `--no-network`, or a fetch is blocked | score `--content` + `--robots`; exclude llms.txt and re-normalize the scorecard | "Offline — scored content + supplied robots; `--url` would add llms.txt + live robots." |
| No robots supplied | neither `--robots` nor a live robots is available | exclude `ai_crawler_access` from the scorecard and say so | "No robots data — crawler-access category excluded; pass `--robots` or `--url`." |
| Unreadable `--robots` file | open() raises | emit a JSON error and exit non-zero (does not invent a verdict) | "Could not read robots file — here is the expected path." |
| Empty / no content | `--content` missing or unreadable | report the error; score only the signals that exist | "No content scored — pass `--content`; the passage categories are excluded." |
| Internal / metadata URL | shared `net_safety` guard refuses it | no fetch happens; report the blocked URL | "Refused an internal/metadata URL (SSRF guard); supply a public URL or `--content`." |

## Dependencies

- `scripts/seo/geo_check.py` (required) — Python 3.10+, standard library only
- `seo-schema` (structured data); optional DataForSEO (LLM-mention tracking)
- Related: `seo-content` (shares the citability lens; one-directional graph)

## Notes

"AI visibility" here means **optimizing** content to get cited (the free, on-page
path); to **measure/track** LLM mentions with hard data, use `seo-dataforseo` (paid MCP).

GEO moves fast — the AI-crawler list lives in one place, `scripts/seo/ai_crawlers.py`
(`--list` prints it; `--generate citable-no-training` emits a ready robots.txt block),
and the dated landscape facts (AI Overviews / AI Mode sourcing, Google-Extended scope,
llms.txt confidence) live in `references/shared/search-landscape-2026.md`. Refresh both
quarterly.
The checker degrades gracefully offline (score content with `--content` alone).
