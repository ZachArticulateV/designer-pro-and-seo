---
name: blast-prompt
description: Generate a complete build brief using the BLAST framework — Blueprint, Link, Architect, Stylize, Trigger. Trigger when the user says "blast prompt", "build brief", "structured build prompt", "give me a complete build prompt", or is about to hand off a site/app build to an AI agent and wants the brief structured.
---

# blast-prompt

**Family:** build-and-qa
**Status:** Stable

## Purpose

Produce a structured, complete build brief in BLAST format so a build agent
(Claude Code, Cursor, etc.) can one-shot a high-quality build. Five sections, each
with a required-fields checklist so nothing is forgotten before launch:

- **Blueprint** — what's being built (pages, sections, features, audience, fidelity)
- **Link** — integrations & external dependencies (forms, payments, analytics, CRM)
- **Architect** — stack, file structure, data flow, performance budget
- **Stylize** — design system reference (palette, type, effects, anti-patterns)
- **Trigger** — the actual paste-ready command for the build agent

## Triggers

- "blast prompt" / "build brief"
- "structured build prompt"
- "complete prompt for the build agent"
- "give me a brief I can paste into Claude / Cursor"

## Inputs

- Project goal (one sentence)
- Stack preference (or "agent picks")
- Existing design system (or "generate one")
- Integrations needed
- Target deployment

## Steps

1. **Load the template** `templates/blast-template.md`.
2. **Walk each section** with the user, filling required fields. Auto-fill from
   project context where possible (CLAUDE.md, an existing design system / `MASTER.md`).
3. **Pull the Stylize section** from a `design-system-gen` result (run it first if
   no design system exists). Map palette hex, typography, and effects into the slots.
4. **Validate completeness.** Run the template's completeness gate — every required
   field filled, no "TBD". For integrations and secrets, list **names only, never
   secret values**.
5. **Write the Trigger.** Compose a single, self-contained, paste-ready launch
   command that references the four sections above so the build agent has full
   context in one paste.
6. **Render** both a Markdown brief and a plain-text version for CLI paste. Offer
   to launch directly or hand off to `parallel-build` for multi-variant builds.

## Outputs

- Markdown brief in BLAST format (from the template)
- Plain-text version for paste-into-CLI
- A completeness gate confirming the brief is launch-ready

## Dependencies

- `templates/blast-template.md` (required)
- `design-system-gen` — for the Stylize section

## Notes

The framework's value is structure-as-coverage: forcing five distinct sections
surfaces gaps (e.g. a forgotten analytics integration) before the build, not
halfway through it. Pairs with `qa-gate` as the bookend — BLAST starts a build,
qa-gate ends it.
