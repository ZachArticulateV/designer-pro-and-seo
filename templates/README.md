# templates/

Prompt templates and starter files referenced by skills. Skills load these on-demand rather than embedding them inline.

## Shipping templates

- `blast-template.md` — Blueprint / Link / Architect / Stylize / Trigger build-brief structure (used by `blast-prompt`)
- `dimensions-template.md` — 5 Core Dimensions design brief (used by `design-dimensions`)
- `qa-report-template.md` — 9-phase QA gate output structure (used by `qa-gate`)
- `design-system-starter.md` — empty design system MASTER.md ready to populate (used by `design-system-persist`)
- `outreach-message-starter.md` — niche-anchored cold-email skeleton (used by `client-outreach`)
- `outreach-followup-sequence.md` — 4–7 touchpoint cadence (used by `client-outreach`)

## Roadmap (not yet shipped)

Planned but not built; nothing references these yet:

- `csv-to-report-prompt.md` — paste-ready prompt for CSV-to-report flow
- `competitive-report-template.md` — interactive HTML scoring report shell
- `content-brief-template.md` — competitive content brief structure
- `local-business-schema-template.json` — LocalBusiness JSON-LD starter

## Status

In use. Six templates present (listed under Shipping templates). More added as skills ship.

## Conventions

- Markdown for narrative templates; JSON for schema templates
- Use `{{variable}}` syntax for interpolation slots
- Include a frontmatter block noting which skill(s) use the template
- Keep templates self-explanatory — a future user opening just the template should understand its purpose
