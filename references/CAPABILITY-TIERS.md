# Capability Tiers — the tool-aware routing contract

Every skill that *can* use an external capability (web crawling, SERP/keyword
data, backlinks, image generation, browser QA, competitive research) routes
through the **same four-tier cascade**. The skill adapts to whatever is available
in the user's session instead of hard-depending on any one paid tool.

This is the plugin's core promise restated operationally: **the free/built-in path
is the product; dedicated tools only deepen it; nothing ever just fails.**

---

## Why routing lives in skill instructions (not code)

There is **no supported API** for a skill or script to enumerate the MCP servers
connected in a Claude Code session. So MCP availability cannot be probed up front —
it is discovered by *trying*. The cascade is therefore written into each skill body
as a try-then-fallback chain:

> Attempt the dedicated tool (Tier 1). If the tool isn't exposed in the session, or
> the call errors, **follow the written fallback** — don't stop.

What *can* be detected from a script — CLI connectors on PATH and which API-key env
vars are set — is reported by `scripts/workflow/capability_probe.py`. Use it to
decide Tiers 3–4 and to tell the user what to install.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/capability_probe.py"            # JSON: {cli, env, notes}
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/capability_probe.py" --human    # ASCII summary
```

The probe never reads or prints secret *values* — only whether each key is set.

---

## The four tiers

| Tier | What | When it runs |
|---|---|---|
| **1 — Dedicated** | A purpose-built MCP/API (DataForSEO, Firecrawl, a GSC MCP, a paid image API) | The MCP tool is exposed in the session, or the API key is set. Try it first. |
| **2 — Built-in** | Claude's own tools (WebFetch, WebSearch, the bundled Playwright MCP) + this plugin's stdlib scripts | Tier 1 absent or errored. **This is the product** — it must produce a real, useful result on its own. |
| **3 — CLI connector** | A local CLI the user already has (e.g. `gemini` for image generation) | Tier 1–2 can't do it but `capability_probe` shows the CLI on PATH. |
| **4 — Guided prompt** | A manual checklist + concrete setup options + links | Nothing above is available. Never fail silently — hand the user a real manual path and name what to install to unlock a higher tier. |

**Always report which tier ran.** End every external-capability skill run with one
line, e.g. *"Source: Tier 2 (built-in WebFetch + tech_audit.py). Install a
DataForSEO MCP to add live keyword volume/CPC (Tier 1)."*

---

## Capability → tier map (seed rows)

The dedicated-tool column is *preferred-if-present*, never required.

| Capability | Tier 1 (dedicated) | Tier 2 (built-in / scripts) | Tier 3 (CLI) | Tier 4 (guided) |
|---|---|---|---|---|
| **Web crawl / scrape** | Firecrawl MCP | WebFetch + `html-extract`; `sitemap_tools.py` for coverage | — | manual fetch checklist + "add Firecrawl MCP" |
| **SERP / keywords** | DataForSEO MCP; a GSC MCP | WebSearch read (no volume/CPC) | — | "add DataForSEO for volume/difficulty" |
| **Backlinks** | Moz / Bing / DataForSEO MCP | WebSearch mention/linking-domain discovery (qualitative); fold in public web-graph data only if you have access | — | "add a link-data MCP for full profiles" |
| **Image generation** | nanobanana MCP / provider API key | — | `gemini` CLI image-gen | prompt to set a key or install the CLI, with options |
| **Browser / visual QA** | Playwright MCP | static a11y/structure checks via existing scripts | — | manual visual-QA checklist |
| **Competitive research** | Firecrawl MCP | WebFetch + WebSearch + `html-extract` | — | manual research checklist |
| **CWV field data** | Google CrUX/PSI (key) | `tech_audit.py` guidance (lab heuristics only) | — | "add a Google API key for field CWV" |

---

## Copy-paste skill section

Add this section to any skill that uses an external capability (place it after
`## Steps`, before `## Outputs`). Replace the bracketed parts for the skill's
capability; delete tiers that don't apply (e.g. drop Tier 3 if there's no CLI).

```markdown
## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`). It adapts to what's available and never fails:

1. **Tier 1 — [dedicated tool].** If [MCP/API] is available, use it for [what it adds].
2. **Tier 2 — built-in (the default).** Otherwise use [WebFetch/WebSearch/Playwright
   + which plugin script]. This produces [the real free-path result].
3. **Tier 3 — CLI connector.** If [`cli`] is on PATH (check `capability_probe.py`),
   use it for [what it adds].  *(omit if N/A)*
4. **Tier 4 — guided.** If none are available, deliver [the manual checklist] and
   name what to install to unlock a higher tier.

Always end by stating which tier ran and what a higher tier would add.
```

---

## Promotion note

A skill reworked onto this cascade ships **Stable** only when its **Tier 2 path is
fully specified and genuinely useful on its own** and it passes the promotion
checklist in `SHIPPING.md`. If a capability has no real built-in path (Tier 2 is
empty and only Tier 1/3 can do it), the skill stays **In development** and says so
honestly — the cascade is a promise, not a coat of paint.
