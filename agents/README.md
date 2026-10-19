# agents/

**13 dispatched-leaf subagents.** These are the specialists that orchestrators such as
`seo-audit`, `qa-gate` and `design-research` fan out to in parallel through the Agent
tool. Each agent wraps its sibling skill in `skills/<name>/` with **no forked logic**:
- the same tier cascade
- the same free path
- the same bundled script

It adds only a machine-parseable `## Output contract` block, so the orchestrator can
merge results deterministically.

| Agent | Dispatched by | Engine it runs | Tools |
|---|---|---|---|
| `seo-technical` | seo-audit (always) | `tech_audit.py` | Read, Glob, Grep, Bash |
| `seo-page` | seo-audit (always), qa-gate | `tech_audit.py` + `content_audit.py` | Read, Grep, Bash |
| `seo-schema` | seo-audit (always) | `schema_gen.py --html / --graph` | Read, Glob, Grep, Bash |
| `seo-sitemap` | seo-audit (always) | `sitemap_tools.py` + `link_graph.py` | Read, Glob, Grep, Bash |
| `seo-image-audit` | seo-audit (always) | `image_audit.py` | Read, Glob, Grep, Bash |
| `seo-content` | seo-audit (conditional) | `content_audit.py` + `geo_check.py` | Read, Glob, Grep, Bash |
| `seo-geo` | seo-audit (conditional) | `geo_check.py` + `llms_txt.py` | Read, Glob, Grep, Bash |
| `seo-ecommerce` | seo-audit (conditional) | `product_audit.py` | Read, Glob, Grep, Bash |
| `seo-local-unified` | seo-audit (conditional) | `nap_check.py` + `geogrid.py` | Read, Glob, Grep, Bash, Write |
| `seo-google` | seo-audit (when a key is set) | CrUX / PSI / GSC, else `tech_audit.py` | Read, Glob, Grep, Bash |
| `seo-backlinks` | seo-audit (when a source is set) | built-in web search / connectors | Read, Grep, WebSearch |
| `design-accessibility` | qa-gate, design-build | `a11y_static.py` (axe with Playwright) | Read, Glob, Grep, Bash |
| `design-visual-qa` | qa-gate, design-build | Playwright screenshots + vision | Read, Glob, Grep, Bash, Write |

## Rules the release gate enforces

- **Least privilege (C5).** Grant only the tools the method uses. An agent that runs
  a bundled fetcher gets `Bash` and **never** `WebFetch` / `WebSearch` alongside it.
  No agent holds `Task`, because agents never dispatch agents.
- **Parity (C3).** Every specialist named in an orchestrator's dispatch block has
  exactly one file here, and every file here is dispatched by someone.
- **Honest output.** The output contract states which tier ran, lists anything that
  needs a paid tier under `needs_tier1`, and never reports a synthesized number.

`_TEMPLATE.md` is the authoring scaffold for a new agent. It is excluded from the
roster, as is this README. The full spec is `references/ENGINE-CONTRACTS.md` §11.
