# Extension: Firecrawl (crawling, scraping, JS rendering)

**Enables:** multi-page crawling, JS-rendered page scraping, and site mapping.

**Used by:** `seo-firecrawl`, `seo-audit` (site-wide crawl), `design-research`
(competitor scraping).

## Install

1. Get a Firecrawl API key (free tier available; paid for volume).
2. Set environment variable `FIRECRAWL_API_KEY`.
3. Merge `.mcp.json` into your Claude Code MCP config; verify `firecrawl` tools.

> The `.mcp.json` pins `firecrawl-mcp@3.20.6` (verified on npm) for reproducible
> installs. Bump the version in `args` if you want a newer release.

## Graceful degradation

Without Firecrawl, crawl-dependent skills fall back to single-page fetches and tell
you what a full crawl would add. `design-research` can still analyze pages you
supply manually. Respect target sites' robots.txt and Terms of Service when
crawling (see PRIVACY.md).
