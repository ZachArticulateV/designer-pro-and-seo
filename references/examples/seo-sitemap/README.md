# Golden example — seo-sitemap (Tier-2: `sitemap_tools.py`)

Proves the **free Tier-2** path of `seo-sitemap` validates a sitemap
deterministically with no network and no API key — the `site-map` capability's
built-in product. Reproducible offline.

## Input

- `sample-sitemap.xml` — a small, well-formed `urlset` with three absolute-URL
  entries and `lastmod` dates.

## Commands

Both halves of the Tier-2 contract run offline against the sample, with no network and
no API key.

**1 — structure validation (`sitemap_tools.py`):**

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/sitemap_tools.py" \
  --validate references/examples/seo-sitemap/sample-sitemap.xml
```

**2 — robots + sitemap-recursion URL inventory (`site_map.py`):**

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/site_map.py" \
  --file references/examples/seo-sitemap/sample-sitemap.xml --no-network --human
```

(From the repo root during development, drop `${CLAUDE_PLUGIN_ROOT}/` and run the
bare `scripts/...` path.)

**3 — quality gates against supplied page states (`sitemap_tools.py --crosscheck`):**

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/sitemap_tools.py" \
  --crosscheck references/examples/seo-sitemap/sample-sitemap.xml \
  --pages references/examples/seo-sitemap/pages.json
```

**4 — internal-link architecture of a 9-page static build (`link_graph.py`):**

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/link_graph.py" \
  --dir references/examples/seo-sitemap/site --base-url https://example.test --human
```

## Expected free deliverable (Tier 2)

1. **Validation:** `"valid": true`, `"url_count": 3`, `"issues": []`, `"score": 100`.
   The sample is clean.
2. **Inventory:**
   ```
   # SITEMAP / URL INVENTORY: references/examples/seo-sitemap/sample-sitemap.xml
   mode=offline-file  source=sitemap  base=https://example.test/
   counts: total=3 internal=3 external=0 disallowed=0
   by page-type: home=1, page=2
   ```
3. **Gates: score 82/100.**
   - G4 (high): `/benches` canonicalizes to `/benches/classic`.
   - G2 (medium): `/care-guide` 301s to `/guides/cedar-care`.
   - G5 (medium): `/guides/cedar-care` is indexable but missing from the sitemap.
4. **Link graph: 9 pages, max depth 5, score 64/100.**
   - L1 (high): orphan cedar-care guide.
   - L3 (high): broken porch-swing link.
   - L4 (medium): finish/stain pages 4–5 clicks deep.
   - L5 (medium): contact is a dead end.
   - L6 (medium): about/contact linked from nav/footer only.
   - L7 (medium): the specs page is reached only by "Click here".

No network, no key. `tests/test_sitemap_linkgraph.py` pins all four results. A live
`--check-live` sample or a Firecrawl crawl (Tier 1) replaces `pages.json` with real
page states.
