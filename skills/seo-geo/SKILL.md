---
name: seo-geo
description: Generative Engine Optimization for AI Overviews, ChatGPT, Perplexity, and Bing Copilot — passage-level citability scoring, llms.txt, AI-crawler accessibility, structured-data signals, and brand-mention guidance. Trigger when the user says "AI Overviews", "SGE", "GEO", "AI search", "LLM optimization", "Perplexity", "AI citations", "ChatGPT search", "AI visibility", or "llms.txt".
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
- "AI search" / "LLM optimization" / "AI visibility" / "ai citations"
- "perplexity" / "chatgpt search" / "bing copilot" / "llms.txt"

## Inputs

- A page URL and/or its content (file)
- Target platforms (AI Overviews / Perplexity / ChatGPT / all)

## Steps

1. **Run the GEO checker:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/geo_check.py" --content page.html --url https://site.com --human
   ```
   It scores passage citability (specificity + standalone readability), counts
   structured-data blocks, checks for `/llms.txt`, and reads the robots.txt
   AI-crawler policy.
2. **Passage citability** — rewrite the weak passages it lists so each states one
   specific, sourced claim (number/date/named source) that survives extraction.
3. **llms.txt** — if absent, create a Markdown `/llms.txt` summarizing the site's
   key pages for LLMs.
4. **AI-crawler access** — ensure retrieval bots (OAI-SearchBot, PerplexityBot,
   Claude-SearchBot) are allowed so the site stays citable, even if training
   crawlers are blocked.
5. **Structured data** — add Article/Organization/Breadcrumb schema via `seo-schema`.
6. **Brand mentions** — recommend earning mentions on sources LLMs trust; if the
   DataForSEO extension is present, pull LLM-mention tracking, else note it.
7. **Render** platform-specific action items (AI Overviews favors structured,
   sourced answers; Perplexity favors fresh, citation-dense pages).

## Outputs

- Passage citability score + the specific weak passages to fix
- llms.txt + AI-crawler-policy status and recommendations
- Structured-data + brand-mention action items, per platform

## Dependencies

- `scripts/seo/geo_check.py` (required) — Python 3.10+, standard library only
- `seo-schema` (structured data); optional DataForSEO (LLM-mention tracking)
- Related: `seo-content` (shares the citability lens; one-directional graph)

## Notes

"AI visibility" here means **optimizing** content to get cited (the free, on-page
path); to **measure/track** LLM mentions with hard data, use `seo-dataforseo` (paid MCP).

GEO moves fast — refresh the llms.txt guidance and AI-crawler list periodically.
The checker degrades gracefully offline (score content with `--content` alone).
