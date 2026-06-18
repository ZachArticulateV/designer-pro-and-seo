# references/

Deep documentation that skills load on-demand. Lives here (not inline in SKILL.md) to keep skill bodies short and discoverable.

## What goes here

- Protocol-level docs that several skills share (e.g., `parallel-build-protocol.md`)
- WCAG checklists, axe rule references, Schema.org type references
- Industry-vertical guides (restaurant SEO checklist, healthcare LocalBusiness specifics)
- Platform-specific quirks (WordPress block escaping, GoHighLevel embed limits, Webflow CMS bindings)
- Source attribution notes (which external concepts informed which skill, link to the original where appropriate)
- Inspiration captures from `html-extract` (saved to `references/inspiration/`)

## What doesn't go here

- Per-skill operational docs — those belong in the skill's SKILL.md or in `templates/`
- Generated reports — those belong in project workspaces, not the plugin

## Status

In use. Present: `PROVENANCE.md` (clean-room ledger), `ENGINE-CONTRACTS.md`
(interface spec), `examples/` (golden outputs for shipping skills). Grows as more
skills ship.

## Subfolder convention

- `references/wcag/` — WCAG 2.2 quick references, axe rule details
- `references/schema/` — Schema.org type cheatsheets
- `references/platforms/` — WP / GHL / Webflow / Wix / Framer / Squarespace specifics
- `references/verticals/` — industry-specific SEO guides
- `references/inspiration/` — html-extract outputs (gitignored or per-project)
- `references/protocols/` — multi-skill workflows (parallel-build, qa-gate)
