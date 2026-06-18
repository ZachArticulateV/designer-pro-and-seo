# Engine Contracts & Authoring Conventions

The interface spec every skill body, script, and template in this plugin must
follow. Designed **before** filling skill bodies so the interface is stable and we
don't harden a bad one. If a skill violates a contract here, the skill is wrong.

---

## 1. SKILL.md structure (canonical order)

Every `SKILL.md` uses this exact section order:

```
---
name: <kebab-case, matches folder>
description: <one line: what it does + "Trigger when the user says ...">
---

# <name>

**Family:** <build-and-qa | design | seo | content-and-data | business-and-gtm | routing>
**Status:** <Stable | In development — ...>

## Purpose
## Triggers
## Inputs
## Steps
## Outputs
## Dependencies      <-- Dependencies ALWAYS before Notes
## Notes
```

Rationale for Dependencies-before-Notes: dependencies are operational (the agent
needs them to run the skill); notes are context. Operational content comes first.
Existing scaffolds may still show Notes-before-Dependencies; fix on next edit.

## 2. Naming convention

- **Family-prefixed** names for skills that belong to a coherent family and are
  usually invoked through an orchestrator: `seo-*`, `design-*`, `route-*`.
- **Bare action names** for standalone, cross-family *workflow* skills that aren't
  owned by one family: `qa-gate`, `parallel-build`, `blast-prompt`,
  `portable-html-port`, `html-extract`, `client-outreach`, `csv-to-report`.

This is deliberate, not an inconsistency: the prefix signals family membership;
its absence signals a top-level workflow. Do not rename existing skills (it breaks
cross-references); apply the rule to new skills.

## 3. Trigger-qualification rule (prevents wrong-skill firing)

Generic verbs (`audit`, `review`, `check`, `generate`, `build`, `optimize`,
`analyze`, `report`) MUST be domain-qualified in the `Triggers` list. Never list a
bare generic verb as a trigger.

- ✅ "seo audit", "wcag audit", "technical audit", "backlink audit"
- ❌ "audit", "audit this"
- ✅ "review the code you wrote", "review this design", "conversion review"
- ❌ "review", "review this"

Cross-domain skills (the `route-*` family especially) must scope their triggers to
their actual lane — e.g. routing-review triggers on *Claude's own output*
("review the code you wrote", "check your work"), not on bare "audit this", which
belongs to the SEO/QA families.

## 4. Dependency direction (must form a DAG)

`Dependencies` lists what a skill *calls*. Edges must be one-directional:
**orchestrator → specialist**, never back. A specialist must not list its
orchestrator as a dependency. If two skills genuinely relate but neither owns the
other, reference each other under **Notes ("Related skills")**, not under
Dependencies. (Cross-references in prose are fine; hard Dependency cycles are not.)

Known hubs (many depend on them): `design-system-gen`, `seo-schema`,
`seo-dataforseo`. Keep their own Dependencies minimal.

## 5. Graceful degradation (the free path is the product)

Most users will not have paid MCPs (DataForSEO, Firecrawl, nanobanana) or Google
API auth. Therefore:

- Every skill that *can* use an optional tool MUST also have a **free/manual
  path** that produces real value without it.
- At runtime the skill must **detect** whether the optional tool is available
  (see §6) and:
  1. If present → use it.
  2. If absent → run the free path AND print one line stating what the paid path
     would add. Never just fail or return nothing.
- The `Dependencies` section must label each dependency `(required)` or
  `(optional — adds X; free path: Y)`.

## 6. Dependency detection pattern

Skills detect optional tooling before using it:

- **CLI tools** (python, node, playwright, codex, gemini): check availability and
  fall back. On Windows the Python launcher is `py`; on macOS/Linux it's
  `python3`. Scripts must be invoked in a way that works on both, or the skill
  must try `python3` then `py`.
- **MCP servers** (Firecrawl/DataForSEO/nanobanana): check whether the MCP tool is
  exposed in the session; if not, state the install path (see `extensions/`).
- **API credentials**: read from environment variables only; if missing, run the
  free path and tell the user which env var to set.

## 7. Scripts contract (`scripts/`)

- Python 3.10+, **standard library preferred**; declare any dep in a per-folder
  `requirements.txt`.
- Each script is runnable standalone (CLI) **and** importable as a library.
- **stdout = machine-readable JSON by default**; add a `--human` flag for ASCII.
- **Idempotent**: same inputs → same outputs.
- Tolerate partial data (e.g. the design engine works with whatever CSVs exist
  and notes which dimension fell back to heuristics).
- Exit non-zero on real failure with a clear stderr message.

## 8. Secrets handling (hard rule)

- Never hard-code credentials. Read from environment variables.
- **Never** print or log API keys, tokens, or secrets to stdout, files, or
  reports — including in error messages and debug output.
- Never write scraped client data outside the user's project workspace.
- Respect target sites' robots.txt and Terms of Service when crawling.

## 9. Acceptance criteria (a skill is "done" only when…)

See `SHIPPING.md` → "Promotion checklist". In short: real Steps, all referenced
assets exist, graceful degradation works, description matches behavior, a golden
example exists under `references/examples/`, and Status reads `Stable`.

## 10. Output filing convention

Skills write generated artifacts into the **user's project workspace**, not into
the plugin. The plugin ships read-only content (skills, scripts, data, templates,
references). Generated reports, design systems, screenshots, and HTML go to the
project the user is working on.
