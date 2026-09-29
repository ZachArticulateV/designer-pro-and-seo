---
name: seo-drift
description: Git-for-SEO — capture baselines of on-page SEO-critical elements and diff against them to catch regressions a deploy introduced (title changed, canonical flipped, noindex added, schema removed). Stores baselines in a local SQLite history so you can compare and trend over time. Trigger when the user says "SEO drift", "SEO baseline", "track changes", "did anything break", "SEO regression", "compare SEO", "before and after deploy", "monitor SEO changes", or "deployment check".
---

# seo-drift

**Family:** seo
**Status:** Stable

## Purpose

Baseline + diff for SEO state — "git for SEO." Capture a page's SEO-critical elements,
store the snapshot, then after a deploy or content change diff a fresh capture against
the stored baseline to catch silent regressions before they cost rankings. Two modes:
a quick one-off **JSON baseline** (`drift_tools.py`), or a **local SQLite history**
(`drift_baseline/compare/history`) that remembers every snapshot so you can compare and
trend over time. Works offline on local HTML or by fetching a URL through the shared
SSRF guard.

## Triggers

- "seo drift" / "baseline" / "deployment check"
- "track changes" / "did anything break" / "seo regression"
- "compare seo" / "before and after" / "monitor seo changes"

## Inputs

- A URL (fetched, SSRF-guarded) or local HTML file
- Mode: a one-off JSON baseline+diff, or a stored SQLite baseline / compare / trend
- Optional: a `--db` path (default `<cwd>/.seo-drift/baselines.db` under your workspace;
  it refuses to default *inside* the plugin — run from your project, or pass `--db` to a
  path under your workspace), a `--label` (e.g. `prod`, `pre-deploy`), a `--baseline-id`

## Steps

1. **Capture a baseline into the SQLite store** (before a deploy, or at handoff):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/drift_baseline.py" --url <URL> --db .seo-drift/baselines.db --label pre-deploy   # or --file page.html; add --robots robots.txt for rule D15
   ```
   Records title, meta description, h1, canonical, meta robots, OG tags, schema-block
   count, h2 count, and word count (the canonical capture set from `drift_tools.py`),
   tagged with a timestamp and label, indexed by URL.
2. **Compare after a change** against the stored baseline:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/drift_compare.py" --url <URL> --db .seo-drift/baselines.db
   ```
   Resolves the latest baseline for that URL (or `--label` / `--baseline-id`), captures
   fresh, and runs the severity engine. It treats **adding `noindex`/`nofollow`** and a
   **canonical flip or drop** as **critical**, **title / h1 / schema-loss** changes as
   **high**, and meta-description / OG / h2 / word-count drift as **advisory** (word-count
   moves under 20% are suppressed as editing noise). Full rationale:
   `references/seo-drift/severity-model.md`.
3. **Trend the history** to see drift across deploys:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/drift_history.py" --url <URL> --db .seo-drift/baselines.db --trend
   ```
   Lists stored baselines, or with `--trend` reports the per-transition change count and
   critical/high/advisory tally — a regression timeline where a deploy that quietly added
   noindex shows up as a critical-count spike.
4. **Quick one-off (no store):** for a single before/after without history, use the
   original JSON path — `drift_tools.py --capture --out baseline.json`, then
   `drift_tools.py --diff --baseline baseline.json`. Same capture set; the JSON baseline
   is a plain file you can commit.
5. **Interpret.** Walk the regressions worst-first: intended change or accident? Fix any
   critical/high immediately. The store design is documented in
   `references/seo-drift/sqlite-schema.md`.

## Outputs

| Output | What it contains | Format | Quality bar (how it is scored) |
|---|---|---|---|
| Stored baseline | A captured SEO-element snapshot tagged with url / label / timestamp, in a local SQLite db | SQLite row (snapshot as JSON) + `--human` ASCII | Capture is deterministic given the same input + `--captured-at`; written under the user's workspace, never the plugin |
| Compare report | Changed elements with before/after, each carrying a rule code (D1–D14), severity tier, and a plain-language note | JSON (default) + ASCII `--human` | Sorted critical → high → advisory; severity comes from the captured-element model, not a guess; "no SEO drift detected" when nothing material changed |
| Trend timeline | Per-transition change count + critical/high/advisory tally across the stored history | JSON `transitions[]` / ASCII `--human` | One transition per consecutive snapshot pair; counts reproduce the compare engine exactly |
| Severity verdict | The tier per change + why (de-index risk vs primary signal vs secondary) | tier label + note | No fabricated magnitude — severity is a structural judgment, never an invented traffic/ranking number |

Filed to: the user's project workspace (the SQLite db and any JSON baselines), never the
plugin. The engine never estimates a traffic or ranking-position impact from a diff —
that would be a synthesized number.

## Error Handling

| Condition | Detection | Behavior (degrade, never fail) | User-facing message |
|---|---|---|---|
| No network / offline | fetch raises or `--no-network` set | run the offline `--file` path (the canonical capturer reads local HTML) | "Offline — analyzed the provided file; a live URL would capture the deployed page." |
| Blocked / internal URL | the shared `net_safety.safe_open` guard refuses a private/loopback/metadata host | return no body + the guard's error; never fetch it | "That URL resolves to a non-public address — refused by the SSRF guard." |
| Bad / empty input | no `--file` and no reachable `--url` → JSON `{"error"}` + non-zero exit | report the validation error; capture nothing | "Provide --file or a reachable --url." |
| No baseline store yet | `drift_compare`/`drift_history` find no db at `--db` → JSON error + non-zero | tell the user to capture first | "No baseline store at <path> — run drift_baseline.py first." |
| No matching baseline | the requested id / label / url isn't in the store → JSON error + non-zero | do not compare against an unrelated baseline | "No stored baseline matches <selector> — capture one or widen the selector." |
| Capture set evolves | `drift_tools.capture()` gains/loses a field | the JSON-blob store needs no migration; severity ignores unknown keys, skips absent ones | (silent — old baselines stay comparable; see the schema reference) |

Every row degrades to a real deliverable — a capture, an honest "no drift," or a clear
next step — never an empty failure.

## Dependencies

- `scripts/seo/drift_tools.py` (required) — the canonical SEO-element capturer + the
  one-off JSON capture/diff path; Python 3.10+, standard library only
- `scripts/seo/drift_baseline.py` (required) — SQLite baseline store + capture-and-store
- `scripts/seo/drift_compare.py` (required) — compare a fresh capture vs a stored baseline
- `scripts/seo/drift_history.py` (required) — list/trend stored baselines
- `scripts/seo/drift_severity.py` (required) — the change→severity engine (rules derived
  from the captured-element set)
- `references/seo-drift/severity-model.md`, `references/seo-drift/sqlite-schema.md`
  (severity-model + store-schema knowledge, loaded on demand)
- All standard-library only; URL fetches route through the shared
  `scripts/workflow/net_safety.py` SSRF guard

## Notes

The SQLite history is the upgrade over a loose JSON file: it remembers every snapshot, so
"compare against the last `prod` capture" and "show me how SEO drifted across the last
five deploys" are one command. The severity tiers are **derived from exactly which
on-page elements we capture** — adding a captured element adds a rule, removing one
silences it (`references/seo-drift/severity-model.md`). A critical verdict means "a human
must confirm this was intended," not "this is a bug" — a planned migration legitimately
flips canonicals; the engine's job is to make sure that flip is never *silent*.

Related: pairs with `design-visual-qa` for a complete pre/post-deploy regression net —
drift catches SEO, visual-qa catches rendering (one-directional reference; neither
depends on the other). Baselines are plain SQLite/JSON you can commit.
