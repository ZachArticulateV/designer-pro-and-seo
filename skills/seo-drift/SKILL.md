---
name: seo-drift
description: Git-for-SEO — capture baselines of on-page SEO-critical elements and diff against them to catch regressions a deploy introduced (title changed, canonical flipped, noindex added, schema removed). Trigger when the user says "SEO drift", "baseline", "track changes", "did anything break", "SEO regression", "compare SEO", "before and after", "monitor SEO changes", or "deployment check".
---

# seo-drift

**Family:** seo
**Status:** Stable

## Purpose

Baseline + diff for SEO state. Capture a page's SEO-critical elements into a JSON
baseline, then after a deploy or content change, diff against it to catch silent
regressions before they cost rankings. Works offline on local HTML or by fetching a
URL.

## Triggers

- "seo drift" / "baseline" / "deployment check"
- "track changes" / "did anything break" / "seo regression"
- "compare seo" / "before and after" / "monitor seo changes"

## Inputs

- A URL (fetched) or local HTML file
- Mode: capture (save baseline) | diff (compare against a baseline)

## Steps

1. **Capture a baseline** (before a deploy, or at handoff):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/drift_tools.py" --capture --url <URL> --out baseline.json   # or --file
   ```
   Records title, meta description, h1, canonical, meta robots, OG tags, schema
   block count, h2 count, and word count.
2. **Diff after a change:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/drift_tools.py" --diff --url <URL> --baseline baseline.json
   ```
   Reports changed elements ordered by severity. It treats **adding `noindex`** as
   **critical**, title/h1/canonical changes as **high**, and ignores minor
   word-count noise (<15%).
3. **Interpret.** Walk the regressions: intended change or accident? Flag any
   critical/high for immediate fix.
4. **For a set of pages,** capture baselines per URL and diff each after deploy.

## Outputs

- Baseline JSON (one per URL/snapshot)
- Diff report: changed elements with before/after, severity-ordered
- A clear "no SEO drift detected" when nothing material changed

## Dependencies

- `scripts/seo/drift_tools.py` (required) — Python 3.10+, standard library only

## Notes

Pairs with `design-visual-qa` for a complete pre/post-deploy regression net — drift
catches SEO, visual-qa catches rendering. Baselines are plain JSON you can commit.
