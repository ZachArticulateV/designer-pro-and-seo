# extensions/

Optional MCP server wirings. The plugin works without any of these, but several skills become significantly more capable when the corresponding MCP is installed and configured.

## Available extensions

- `firecrawl/` — Firecrawl MCP for crawling, scraping, JS rendering (used by `seo-firecrawl`, `seo-audit`, `design-research`)
- `dataforseo/` — DataForSEO MCP for premium SERP / keyword / backlink / AI-visibility data (used by `seo-dataforseo`, `seo-backlinks`, `seo-cluster`, `seo-content-brief`, `seo-ecommerce`, `seo-geo`, `seo-image-audit`, `seo-local-unified`, `seo-page`, `seo-sxo`)
- `nanobanana/` — Gemini-based image generation (used by `seo-image-gen`; the
  recommended path is the Gemini CLI — see that folder's README)
- `playwright/` — Microsoft's Playwright MCP for browser automation (used by `design-accessibility`, `design-visual-qa`, `design-cro`, `qa-gate`, `html-extract`, `parallel-build`, `portable-html-port`)

## Per-extension setup

Each subfolder will contain:
- `README.md` — what this extension enables, install steps, configuration
- `.mcp.json` snippet — the MCP server config to merge into the user's settings
- Auth / credential guidance (env vars, OAuth steps, free vs paid tiers)

## Status

Wired. Each of `playwright/`, `dataforseo/`, `firecrawl/`, `nanobanana/` has a
`README.md` (setup + graceful-degradation notes) and a `.mcp.json` config snippet.
All are optional — the shipping skills work without them. Package versions in each
`.mcp.json` are **pinned to a version verified on npm** (no floating `@latest`) for
reproducible installs; bump them when you want a newer release.

## What runs when an extension is missing

| Extension | Adds | Free path that runs without it |
|---|---|---|
| `playwright/` | live axe scans, screenshots, real interaction | `a11y_static.py`, `motion_audit.py`, `cro_audit.py`, `qa_gate.py` (phases 2 and 8 marked N/A) |
| `firecrawl/` | full-site crawl, JS rendering | `site_map.py` discovery, `link_graph.py` on a build, `sitemap_tools.py --check-live` sample |
| `dataforseo/` | SERP, keyword, backlink, AI-visibility data | `serp_cluster.py` on supplied SERPs, `geo_check.py`, on-page engines; volumes listed as `needs_tier1` |
| `nanobanana/` | image pixels | an exact image spec (dimensions, alt, OG meta, schema `image`) |

## Design intent

Skills that depend on an extension must degrade gracefully via the plugin's
capability-tier cascade (`references/CAPABILITY-TIERS.md`): if the extension isn't
installed, the skill reports what it can without it (the built-in path) and names
what installing the extension would add. The free/built-in path is the product.
