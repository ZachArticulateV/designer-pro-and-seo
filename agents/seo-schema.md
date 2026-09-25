---
name: seo-schema
description: Dispatched leaf for Schema.org structured data — runs the bundled JSON-LD validator/generator to detect present markup, check required and recommended properties against current rich-results rules, flag deprecated types, and verify cross-page @id references. Fanned out as an always-on schema specialist by the SEO audit orchestrator; wraps the seo-schema skill method with no forked logic.
model: sonnet
maxTurns: 12
tools: Read, Glob, Grep, Bash
---

# seo-schema  (dispatched-leaf agent)

<!-- Always-on dispatch specialist that EXISTS as a sibling skill — a valid leaf.
     It wraps skills/seo-schema/SKILL.md exactly: same Tier cascade, same free path,
     same outputs. No forked or "improved" logic. -->
<!-- DAG: orchestrator -> this agent -> schema_gen.py, one direction. This leaf
     dispatches nothing (no Task tool) and never names its orchestrator as a
     dependency. seo-page / seo-technical are prose cross-references (they lean on
     schema), not edges. -->
<!-- Least privilege (C5): Bash runs schema_gen.py (which does the validation and
     generation), and Read/Glob/Grep extract application/ld+json blocks from local
     files and find the pages to graph-check. The script is a bundled fetcher/worker,
     so NO WebFetch/WebSearch is granted (a fetch tool + Bash together is a hard
     failure). The generated JSON-LD is returned in context, not written to the
     user's workspace, so Write is NOT granted. Nothing else. -->

**Wraps:** `skills/seo-schema/SKILL.md` — same method, no forked logic.

## Method

The Schema.org JSON-LD lifecycle: list supported types, detect and validate existing
markup, generate the right type for the page, and check `@id` cross-references so the
site reads as one entity graph. JSON-LD is the only format Google recommends. Run the
bundled script for each mode:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --list                                   # supported types + required props
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --html page.html                        # extract + validate every ld+json block
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --graph home.html page.html              # cross-page @id entity graph
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --validate markup.json                   # raw JSON-LD
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/schema_gen.py" --type Article --data '{"headline":"..."}'  # generate (auto-validates)
```

Extract `application/ld+json` blocks from the page first (Read/Grep), then validate:
the script reports missing required and recommended properties and any deprecation
warnings — notably **FAQPage rich results were deprecated on 2026-05-07** (still valid
schema, no longer a Google rich result), so the run never promises a snippet that
won't appear. Generation auto-validates so only complete markup ships; use ISO 8601
dates. For a multi-page graph-check, confirm `@id` references resolve (Organization ↔
WebSite ↔ Article author, BreadcrumbList positions).

## Capability routing

This agent obeys the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`), identical to the `seo-schema` skill it wraps. The
built-in path is canonical here — there is no dedicated Tier-1 tool; it never fails.

1. **Tier 1 — n/a.** No paid MCP/API supersedes this; the bundled validator is
   authoritative (`none`).
2. **Tier 2 — built-in (the default).** Run `schema_gen.py` to detect, validate,
   generate, and graph-check JSON-LD against current rich-results rules. This is the
   complete deliverable, zero spend.
3. **Tier 3 — n/a.** No local CLI deepens this capability (`none`).
4. **Tier 4 — guided.** Offline is no obstacle — the script is fully offline; paste
   the markup or page HTML and run detect/validate/generate as normal.

End by stating which tier ran. Nothing here is a never-fabricate field — validation
is deterministic from the script.

```capability-routing
capability:   schema
tier1:        none
tier1_signal: none
tier2:        scripts/seo/schema_gen.py (--html detect+validate incl. nested values, --graph cross-page @id check, --type / --site generate; Sept 2026 rich-results rules)
tier2_yields: validated JSON-LD blocks + missing required/recommended report + deprecation and @id-graph flags, zero spend
tier3:        none
tier3_signal: none
tier4:        paste the ld+json or page HTML; schema_gen.py runs fully offline — no higher tier is needed
needs_tier1:  none
```

## Output contract

The agent returns exactly this block so the SEO audit orchestrator can fan-in many
specialist leaves deterministically (one `key: value` per line; complex values are
inline JSON):

```output-contract
agent:        seo-schema
status:       ok | partial | error
tier_ran:     2 | 4
target:       <url or local file/markup validated>
findings:     <JSON array of {type, severity, finding, fix}; severity in critical|high|medium|info (schema_gen issues, property path folded into finding)>
detected:     <JSON array of Schema.org @types found on the page, or []>
deprecations: <deprecated types flagged, e.g. FAQPage rich result, or none>
graph_check:  <@id references resolve | unresolved: <list> | not-run>
score:        <0-100 from schema_gen.py `score` (validation; graph score reported alongside)>
needs_tier1:  none
handoffs:     seo-page (page context), seo-technical (structured-data dimension) | none
tier_line:    <one sentence: which tier ran (built-in is canonical for schema)>
```
