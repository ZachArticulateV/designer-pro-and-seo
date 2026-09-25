# seo-audit — the dispatch matrix

Which specialist agents the `seo-audit` orchestrator fans out to, and when. The
orchestrator dispatches every **always-on** specialist on every audit, then adds the
**conditional** specialists the business type and connected tooling call for. Each
specialist is a real dispatched-leaf agent under `agents/`; adding a new specialist
agent auto-joins this socket. Knowledge, not steps — the run procedure is in
`skills/seo-audit/SKILL.md`; the fan-in scoring is in `scoring-weights.md`.

## The machine-readable roster

The orchestrator and the release gate read this block. The split is **derived from
this plugin's own specialist set** — five universally-relevant on-page/architecture
checks that run every time, and six that depend on the site or the tools connected —
not from any third-party audit's dispatch shape.

```dispatch
always:      seo-page, seo-technical, seo-schema, seo-sitemap, seo-image-audit
conditional: seo-content, seo-geo, seo-local-unified, seo-ecommerce, seo-google, seo-backlinks
```

## Always-on specialists (every audit)

| Agent | Covers | Why always |
|---|---|---|
| `seo-page` | per-URL review = technical + content audits on one page (two scores) | every page has on-page elements |
| `seo-technical` | 10-dimension technical spine with a lab score (crawlability + AI-crawler policy, indexability incl. X-Robots-Tag / 2 MB limit, security, URL, mobile, CWV lab risks, structured data, JS render, SERP presentation) | every site has a technical layer |
| `seo-schema` | JSON-LD validation incl. nested values + the cross-page `@id` entity graph | rich-result eligibility and entity clarity apply to any page type |
| `seo-sitemap` | sitemap validation + quality gates + the internal-link graph | discovery/architecture is universal |
| `seo-image-audit` | image SEO (alt quality, formats, srcset, LCP loading, CLS, byte/pixel budgets) | every site ships images |

## Conditional specialists (added by business type / connected tooling)

| Agent | Dispatch condition | Signal |
|---|---|---|
| `seo-content` | any site with substantive content (default-on; skip pure link/nav shells) | content present on the profiled pages |
| `seo-geo` | when AI-citability / AI Overviews matter (default-on for most sites) | text pages that could be cited by AI answers |
| `seo-local-unified` | `business_type` is `local` or `sab`, or a multi-location site | `business_type.py` classification |
| `seo-ecommerce` | a store / product catalog is detected | `business_type` == `ecommerce` (product/Offer markup, cart) |
| `seo-google` | a Google PSI/CrUX/GSC key or MCP is connected | `CRUX_API_KEY` / `GOOGLE_API_KEY` / GSC MCP present |
| `seo-backlinks` | a backlink source is connected (Moz / Bing / Common Crawl / DataForSEO) | connector present, or Common-Crawl free path requested |

`business_type.py` supplies the classification that gates `seo-local-unified` and
`seo-ecommerce`; the two Google/off-page specialists gate on `capability_probe.py`
presence signals. When a conditional specialist is **not** dispatched, its absence is
recorded in the audit's "covered / not covered" list and excluded from the score
denominator (see `scoring-weights.md`) — never silently zeroed.

## Where each specialist's score comes from

Every score is deterministic and built only from observed signals; a specialist with no
score is excluded from the denominator, never zeroed. `scripts/workflow/site_audit.py`
produces all of the local ones in one command for a static build.

| Specialist | Engine | Score |
|---|---|---|
| `seo-technical` | `tech_audit.py` | lab score (100 − 25/critical − 10/high − 4/medium) |
| `seo-page` | `tech_audit.py` + `content_audit.py` | mean of the two |
| `seo-content` | `content_audit.py` | content score |
| `seo-schema` | `schema_gen.py --html` / `--graph` | validation score (graph score alongside) |
| `seo-sitemap` | `sitemap_tools.py` + `link_graph.py` | validation score (gates + graph alongside) |
| `seo-image-audit` | `image_audit.py` | image score |
| `seo-geo` | `geo_check.py --scorecard` | weighted GEO score |
| `seo-ecommerce` | `product_audit.py` | merchant / category score |
| `seo-local-unified` | `nap_check.py` + `geogrid.py` | needs supplied listings / rank data |
| `seo-google`, `seo-backlinks` | connectors | Tier-1 data only; otherwise not scored |

`seo-hreflang` (`hreflang_tools.py --cluster`) joins the local run whenever pages carry
hreflang; it is not a dispatched agent, so it sits outside the roster block below.

## Parity + shape invariants (the release gate enforces)

- **Dispatch == disk.** Every agent named in the `dispatch` block above has exactly
  one `agents/<name>.md` on disk, and every SEO specialist agent on disk is named
  here (many-orchestrator-to-one-leaf hubs are legal). C3 fails a claimed-but-missing
  specialist or an orphaned agent.
- **No third-party dispatch shape.** The always/conditional split is **5 + 6**,
  derived from this plugin's own specialists; the gate fails any 8-always + 7-
  conditional split (do-not-mirror an external roster).
- **DAG.** orchestrator -> agent -> script, one direction; agents never dispatch
  agents.
