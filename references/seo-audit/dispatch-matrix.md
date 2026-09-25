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
| `seo-page` | per-URL on-page review (title/meta/H1/canonical/OG/images/links) | every page has on-page elements |
| `seo-technical` | 10-dimension technical spine with a lab score (crawlability + AI-crawler policy, indexability incl. X-Robots-Tag / 2 MB limit, security, URL, mobile, CWV lab risks, structured data, JS render, SERP presentation) | every site has a technical layer |
| `seo-schema` | structured-data detection + validation | rich-result eligibility applies to any page type |
| `seo-sitemap` | sitemap structure + crawl-architecture gates | discovery/architecture is universal |
| `seo-image-audit` | image SEO (alt coverage, dimensions/CLS, formats, lazy-load) | every site ships images |

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
