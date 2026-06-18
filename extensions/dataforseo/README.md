# Extension: DataForSEO (paid SERP / keyword / backlink data)

**Enables:** live SERP positions, keyword volume/difficulty, backlink profiles,
Google Images rankings, and AI-visibility/LLM-mention data.

**Used by:** `seo-dataforseo`, `seo-page` (optional — adds real ranking/keyword
context), `seo-backlinks`, `seo-cluster`, `seo-content-brief`, `seo-ecommerce`,
`seo-local-unified`, `seo-geo`, `seo-sxo`, `seo-image-audit`.

## Install

1. Create a DataForSEO account and get API credentials (paid, pay-as-you-go).
2. Set environment variables `DATAFORSEO_USERNAME` and `DATAFORSEO_PASSWORD`.
   **Never put credentials directly in the JSON** — the `${...}` form reads them
   from your environment.
3. Merge `.mcp.json` into your Claude Code MCP config. Verify `dataforseo` tools
   appear.

> The `.mcp.json` pins `dataforseo-mcp-server@2.9.8` (verified on npm) for
> reproducible installs. Bump the version in `args` if you want a newer release.

## Graceful degradation (important — most users won't have this)

Every skill above has a **free path** and uses DataForSEO only to *enrich* it:
- `seo-page` runs a complete on-page/technical/schema/image review with **no API**;
  DataForSEO only adds live ranking/keyword context when present.
- Backlink/keyword skills fall back to free sources and clearly label which figures
  would be available with DataForSEO.

The skill detects the credentials/tools at runtime and tells you, in one line,
what the paid path would add — it never silently fails.
