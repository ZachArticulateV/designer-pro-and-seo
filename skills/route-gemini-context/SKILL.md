---
name: route-gemini-context
description: Long-context delegation — hands large multi-file or whole-repo work to Gemini's large context window for architecture maps, refactor-impact analysis, and multi-document synthesis. Trigger when the user says "scan the whole repo", "long context", "all the files", "synthesize across", "gemini analysis", "architecture map", "trace dependencies", "what changes if I refactor X", or when a task needs more context than Claude's window.
---

# route-gemini-context

**Family:** routing
**Status:** Stable

## Purpose

The execution arm for tasks that need a context window bigger than Claude's: whole-
repo architecture maps, refactor-impact analysis, multi-document synthesis, and
large structured-data passes. Gemini returns a synthesized result that Claude then
integrates.

## Triggers

- "scan the whole repo" / "long context" / "all the files" / "synthesize across"
- "gemini analysis" / "architecture map"
- "trace dependencies" / "refactor impact" / "compare these schemas/docs"

## Inputs

- Task description; the file/directory scope; the specific question

## Steps

1. **Check Gemini is available:** `gemini --version`. If absent, tell the user and
   fall back to a scoped Claude pass over the most relevant files (narrower, but
   honest about the limit).
2. **Scope the context** — name the directories/files. For long media (video/PDF),
   preprocess first (cap duration/pages) so you don't blow the context.
3. **Invoke Gemini** with a focused ask and a required output format:
   ```
   gemini -p "Map the architecture. Return a file:line list of where X happens. Cap 800 words." @./src
   ```
   Prefer the adjacent `cc-gemini-plugin` (it packages directories) when available.
4. **Demand citations** — file:line, page numbers, or timestamps — not a flat
   summary, so the result is verifiable.
5. **Integrate** the synthesis into the conversation; spot-check key claims against
   the actual files before acting on them.

## Outputs

- Gemini's synthesized analysis (with file:line / page / timestamp citations)
- A short note of what context was sent

## Dependencies

- The `gemini` CLI installed (or the adjacent `cc-gemini-plugin`). Degrades to a
  scoped Claude pass when absent.

## Notes

Use when the task genuinely needs breadth. For a surgical lookup in a known file,
use Claude directly — Gemini's strength is breadth, not precision. Verify before
acting (recalled/long-context output can drift).
