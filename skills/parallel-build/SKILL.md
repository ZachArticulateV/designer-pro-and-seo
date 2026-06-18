---
name: parallel-build
description: Spin up multiple website or page variants in parallel using git worktrees (or sibling folders) and sub-agents, each with a different inspiration source but the same brief and shared design tokens, for side-by-side comparison. Trigger when the user says "parallel build", "build three versions", "spin up variants", "make 3 sites at once", "side-by-side build", or wants different design flavors to compare.
---

# parallel-build

**Family:** build-and-qa
**Status:** Stable

## Purpose

The multi-variant build primitive: instead of one prompt → one site, spawn N
sub-agents (default 3), each in its own worktree/folder, each given a different
inspiration source but the **same brief and the same design tokens**. The user gets
a side-by-side comparison and cherry-picks the best sections into a merged final.

## Triggers

- "parallel build" / "build three versions" / "spin up variants"
- "make 3 sites at once" / "side-by-side build"
- "different flavors to compare"

## Inputs

- Target (business/page/client) + the brief
- N variants (default 3) and N inspiration sources (one per variant; `html-extract`
  can supply them)
- Output mode: git worktrees | sibling folders

## Steps

1. **Capture** the brief and the N inspiration sources.
2. **Generate shared tokens once** with `design-system-gen` so all variants share a
   coherent palette/type/effects — consistency across variants, distinctiveness via
   inspiration + layout.
3. **Create N output locations** — git worktrees (the `using-git-worktrees` pattern)
   or, if git isn't available, sibling folders `variant-1/ … variant-N/`.
4. **Dispatch N sub-agents in parallel**, each running `design-build` with the same
   brief + shared tokens but its own inspiration source. One-shot each (iterate only
   if needed).
5. **Collect** outputs and render a side-by-side comparison (screenshots via
   `design-visual-qa` if Playwright is present, else a structured summary).
6. **Cherry-pick + merge.** The user picks sections from each; assemble the final and
   run `qa-gate` before delivery.

## Outputs

- N variant builds in their output locations
- A side-by-side comparison artifact
- The merged final (after the user picks)

## Dependencies

- `design-system-gen` (shared tokens), `design-build` (per-variant build), sub-agent
  dispatch; git worktrees (optional — falls back to sibling folders)
- Optional: `html-extract` (inspiration), `design-visual-qa` (comparison shots),
  `qa-gate` (final)

## Notes

Shared tokens + divergent inspiration is the formula: variants feel like one brand
exploring directions, not three unrelated sites.
