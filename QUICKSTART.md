# Quickstart

Get value in five minutes — no paid API required.

## 1. Requirements

- **Claude Code** (this is a Claude Code plugin).
- **Python 3.10+** — for the design engine and helper scripts. Check:
  `python3 --version` (macOS/Linux) or `py --version` (Windows).
- That's it for the shipping skill set. Optional tools below unlock extra depth.

## 2. Install

This repo is its own plugin marketplace. In Claude Code:

```text
/plugin marketplace add ZachArticulateV/designer-pro-and-seo
/plugin install designer-pro-and-seo@designer-pro-and-seo
```

Then `/plugin` should list `designer-pro-and-seo` as enabled.

**Working from a clone?** `claude --plugin-dir designer-pro-and-seo` loads it for
one session, and from the repo root you can verify the bundled scripts:

```text
python3 scripts/smoke_test.py      # use `py` on Windows
```

Expect `32/32 checks passed.`

## 3. First run — the golden path (all free)

Try these in order; each hands off to the next:

1. **Design system** — "generate a design system for a saas-landing in saas,
   modern and trustworthy" → `design-system-gen` runs the local engine and returns
   a full palette/type/effects spec. (See `references/examples/design-system/` for
   a sample output.)
2. **Design brief** — "make a 5-dimension design brief from that" → `design-dimensions`.
3. **Build brief** — "now give me a BLAST build brief" → `blast-prompt`.
4. **QA** — after building: "qa check this build, is it client-ready?" → `qa-gate`.
5. **Port** — "port this to GoHighLevel as single-file HTML" → `portable-html-port`.
6. **SEO** — "check this page's SEO: <url>" → `seo-page`.

## 4. Compatibility matrix (optional tools)

The shipping skills work fully without any of these. Optional tools add depth:

| Skill | Works without extras? | Optional tool | What it adds |
|---|---|---|---|
| `design-system-gen` | ✅ fully | — | — |
| `design-dimensions` | ✅ fully | — | — |
| `blast-prompt` | ✅ fully | — | — |
| `portable-html-port` | ✅ fully | — | — |
| `qa-gate` | ✅ (static path) | Playwright | live a11y/visual/perf verification |
| `seo-page` | ✅ (fetch+parse) | DataForSEO; Google APIs | live rankings/keywords; real CWV field data |

Optional tools are configured per `extensions/<name>/README.md`. Every skill that
can use one **detects it at runtime** and tells you, in one line, what you'd gain —
it never silently fails (see `references/ENGINE-CONTRACTS.md`).

The seven **tool-aware** skills — `seo-google`, `seo-dataforseo`, `seo-firecrawl`,
`seo-backlinks`, `seo-image-gen`, `design-research`, `design-visual-qa` — follow the
same pattern at full depth: a dedicated MCP/CLI when present, else Claude's built-in
web/browser + bundled scripts, else a guided path. Details:
`references/CAPABILITY-TIERS.md`.

## 5. What's shipping vs. in development

See `SHIPPING.md`. **All 45 skills are ✅ Stable.** Every skill that can use an
external tool is *tool-aware*: it uses a dedicated MCP/CLI when present and falls
back to Claude's built-in web/browser tools + bundled scripts otherwise
(`references/CAPABILITY-TIERS.md`), so each has a real free path.

## 6. Troubleshooting

- **`python3: command not found` (Windows):** use `py` instead.
- **A skill needs a tool you don't have:** it runs its free/built-in path and tells
  you what connecting a tool would add (see `references/CAPABILITY-TIERS.md`).
- **Smoke test fails on `color-palettes.csv`:** run
  `python3 scripts/design/gen_palettes.py` to generate it, then re-run.
- More help: `SUPPORT.md`.
