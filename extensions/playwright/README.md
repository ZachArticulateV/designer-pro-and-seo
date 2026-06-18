# Extension: Playwright (browser automation)

**Enables:** real-browser checks — accessibility scans, visual screenshots/diffs,
in-browser CRO/thumb-zone analysis, and the deeper passes of the QA gate.

**Used by:** `qa-gate` (optional, deepens phases 3/4/8), `design-accessibility`,
`design-visual-qa`, `design-cro`, `html-extract`, `parallel-build`,
`portable-html-port`.

## Install

1. Merge `.mcp.json` in this folder into your Claude Code MCP config. It pins
   `@playwright/mcp@0.0.76` (verified on npm); bump the version if you want newer.
2. First run will download browser binaries via `npx @playwright/mcp`.
3. Verify the `playwright` MCP tools appear in your session.

Free and open-source — no API key.

## Graceful degradation

Without Playwright, the skills above still run a **static path**: `qa-gate`
performs heuristic/markup checks and clearly notes which phases need Playwright for
live verification; `design-accessibility` falls back to source-level checks and
recommends installing Playwright for a full axe-core scan. No skill hard-fails for
lack of this extension.
