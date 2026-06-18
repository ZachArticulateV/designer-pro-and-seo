---
name: design-system-persist
description: Save a generated design system to disk as a hierarchical Master + per-page-overrides structure so future sessions can retrieve it for the project. Trigger when the user says "save the design system", "persist this", "make this the master for the project", "remember these design choices", or wants the design system to survive across sessions.
---

# design-system-persist

**Family:** design
**Status:** Stable

## Purpose

Save a design system into a project's `design-system/` folder so it survives across
sessions and is shared across skills. Uses a Master + Overrides pattern:

- `design-system/MASTER.md` — the global system (every page inherits it by default)
- `design-system/pages/<page-name>.md` — per-page overrides (clean deviations)

Future sessions check `pages/<current-page>.md` first; if present, its rules
override Master, else Master applies. A 12-page site gets one Master + small page
files instead of one bloated spec enumerating every exception inline.

## Triggers

- "save the design system" / "persist this"
- "make this the master"
- "remember these design choices"
- "design system to disk"

## Inputs

- A design system spec (from `design-system-gen`, or pasted by the user)
- Project root path
- Page name (optional — for a per-page override)

## Steps

1. **Get the design system.** Use a `design-system-gen` result (JSON or ASCII) or
   the spec the user pasted.
2. **Locate/create** `design-system/` at the project root (and `pages/` if saving
   an override).
3. **Fill the starter template** `templates/design-system-starter.md`: map the
   palette hex + contrast, typography + weights, pattern, style, effects,
   anti-patterns, and the pre-delivery checklist into its slots.
4. **Write the file:**
   - Master → `design-system/MASTER.md`
   - Page override → `design-system/pages/<name>.md` with explicit deviation +
     reason notes (keep deviations minimal).
5. **Write/refresh** `design-system/README.md` explaining the structure to future
   agents.
6. **Emit a retrieval prompt** for the next session, e.g.: *"I'm building [page].
   Read design-system/MASTER.md; also check design-system/pages/[name].md — page
   rules override Master."*

## Outputs

- `design-system/MASTER.md` (and/or `pages/<name>.md`)
- `design-system/README.md`
- A paste-ready context-retrieval prompt for the next session

## Dependencies

- `templates/design-system-starter.md` (required)
- `design-system-gen` (typical upstream)

## Notes

The Master + Overrides shape scales cleanly and keeps the global system as the
single source of truth. Files are written to the user's project workspace, never
into the plugin (see `references/ENGINE-CONTRACTS.md` §10).
