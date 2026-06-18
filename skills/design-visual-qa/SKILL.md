---
name: design-visual-qa
description: Capture visual baselines of a built site at multiple viewports and detect visual regressions against prior baselines, using the bundled (free) Playwright extension to render and Claude's vision to compare; an exact pixel-diff CLI is used for precise deltas when available. Without a browser, delivers a structured manual visual-QA checklist and the one step to enable rendering. Trigger when the user says "visual qa", "visual regression", "screenshot diff", "did anything change visually", "pixel diff", "compare against baseline", or before/after a refactor where the visual output must not change.
---

# design-visual-qa

**Family:** design
**Status:** Stable

## Purpose

Visual regression for the rendered surface — the visual analog of `seo-drift`.
Captures snapshots at multiple viewports and compares them against prior baselines
to catch unintended rendering changes. It is **tool-aware**: rendering uses the
bundled, free Playwright extension; comparison uses Claude's vision by default (and
an exact pixel-diff CLI for precise deltas when one is installed). Without a browser
it can't capture pixels — so it delivers a structured manual visual-QA checklist and
the single step to enable the free renderer, rather than failing.

Use cases: pre/post refactor, pre/post deploy (staging vs prod), component/token
updates, and cross-browser drift.

## Triggers

- "visual qa" / "visual regression"
- "screenshot diff" / "pixel diff"
- "did anything change visually"
- "compare against baseline"
- "before and after screenshots"

## Inputs

- Target URL(s) or local build paths
- Viewports (default: 375, 768, 1280, 1920)
- Browser(s) (default: chromium; optional firefox, webkit)
- Baseline mode: capture | diff | both
- Threshold for "changed" (pixel-diff % when an exact differ is present; otherwise a
  qualitative materiality call)

## Steps

1. **Detect the renderer.** Confirm the Playwright MCP is connected; run
   `scripts/workflow/capability_probe.py` to see if an exact differ (`odiff`/
   `pixelmatch` via `npx`) is available.
2. **Capture.** For each (URL, viewport, browser): load, wait for network idle +
   fonts + animations settled, then full-page screenshot.
3. **Baseline vs diff.**
   - `capture`: save baselines to `visual-qa/baselines/` in the user's workspace.
   - `diff`: compare each shot to its baseline. Exact differ present → pixel-delta %
     + highlighted diff image. Otherwise → Claude-vision comparison reporting the
     specific regions/elements that changed and whether each looks intentional.
4. **Aggregate** which pages/viewports drifted and by how much (or how materially).
5. **Report which tier ran** and, if no browser was available, the one step to enable
   it (connect the bundled Playwright extension).

## Capability routing

This skill follows the plugin's capability-tier cascade
(`references/CAPABILITY-TIERS.md`):

1. **Tier 1/2 — Playwright (bundled, free) + comparison.** Render with Playwright;
   compare with an exact pixel differ if installed, else Claude's vision. This is the
   product.
2. **Tier 4 — guided.** No browser available → deliver a structured manual visual-QA
   checklist (what to eyeball per viewport) and the one step to enable Playwright
   (`extensions/playwright/`). Route static structural/a11y checks to
   `design-accessibility`.

Always state which tier ran and how to enable rendering if it didn't.

## Outputs

Written into the user's project workspace:
- `visual-qa/baselines/<page>-<viewport>-<browser>.png` — baselines
- `visual-qa/diffs/<run-date>/...` — diff images (when an exact differ ran)
- `visual-qa/report-<date>.md` — summary (drifted pages/viewports + severity)

## Dependencies

- Playwright extension (`extensions/playwright/`) — free, bundled; required to
  capture. Without it, the skill runs its Tier-4 guided path.
- Optional: an exact pixel-diff CLI (`odiff`/`pixelmatch` via `npx`) for precise
  deltas; Claude-vision comparison is the default and needs nothing extra.
- `scripts/workflow/capability_probe.py`

## Notes

Pairs with `seo-drift` for a complete "did anything change" picture — drift catches
SEO regressions, visual-qa catches rendering regressions. Comparison defaults to
Claude's vision so no pixel-diff dependency is required for a useful result.
