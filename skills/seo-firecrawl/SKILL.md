---
name: seo-firecrawl
description: Site crawling, mapping, and JS-rendered scraping via the Firecrawl MCP when connected; otherwise builds a URL inventory from the sitemap and does targeted page fetches with the built-in fetcher, naming what a full crawl would add. Trigger when the user says "crawl site", "map site", "full crawl", "find all pages", "broken links", "site structure", "discover pages", "JS rendering", "scrape with javascript".
---

# seo-firecrawl

**Family:** seo
**Status:** Stable

## Purpose

Site-level discovery and scraping. **Tool-aware:** with the Firecrawl MCP connected
it does true multi-page crawling and JS-rendered scraping (for sites where a plain
HTTP fetch returns an empty shell); without it, it builds a URL inventory from the
sitemap and fetches the pages you point it at — a real, useful map on the free path.

## Triggers

- "crawl site" / "full crawl"
- "map site" / "site structure"
- "find all pages" / "discover pages"
- "broken links"
- "JS rendering" / "scrape with javascript"

## Inputs

- Starting URL (and sitemap URL if known)
- Crawl depth / page cap (Tier 1) or the specific pages to fetch (Tier 2)
- Output format (URL inventory | per-page markdown | broken-link list)

## Steps

1. **Detect tooling.** Check whether the Firecrawl MCP is exposed this session
   (`scripts/workflow/capability_probe.py` also reports `FIRECRAWL_API_KEY`).
2. **Crawl path (Tier 1, if connected).** Run the Firecrawl MCP crawl/map/scrape for
   the requested depth; return the URL inventory + per-page markdown + broken links.
3. **Built-in path (Tier 2, always available).** Fetch `sitemap.xml` (or the given
   sitemap) and run `scripts/seo/sitemap_tools.py --validate` to get a structured URL
   inventory; fetch the priority pages with WebFetch; flag fetch failures as likely
   broken links. State that JS-rendered-only content and large-scale crawls need Tier 1.
4. **Report which tier ran** and what a full Firecrawl crawl would add.

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`):

1. **Tier 1 — Firecrawl MCP.** If connected, use it for multi-page crawl, JS
   rendering, and batch scrape.
2. **Tier 2 — built-in (default).** Otherwise `sitemap_tools.py` for the URL
   inventory + WebFetch for targeted pages. Produces a real site map for
   static/server-rendered sites.
3. **Tier 4 — guided.** If the site is JS-rendered and Firecrawl isn't connected,
   deliver the sitemap inventory and note that full rendering needs Firecrawl (or
   the Playwright extension for interaction-heavy pages).

Always state which tier ran and what a full crawl would add.

## Outputs

- URL inventory (from crawl on Tier 1; from sitemap on Tier 2)
- Per-page content as markdown for the pages retrieved
- Broken-link list (crawl-wide on Tier 1; from fetch failures on Tier 2)

## Dependencies

- Optional (Tier 1): Firecrawl MCP (`extensions/firecrawl/`) — adds full crawl + JS
  rendering; free path works without it
- Built-in (Tier 2): WebFetch; `scripts/seo/sitemap_tools.py`
- `scripts/workflow/capability_probe.py`

## Notes

Backbone of `seo-audit` and `design-research` when a full crawl is needed. For pages
that require interaction beyond rendering, pair with the Playwright extension.
