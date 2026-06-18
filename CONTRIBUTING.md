# Contributing

Thanks for your interest in **designer-pro-and-seo** — a free, MIT-licensed Claude
Code plugin developed in the open. Issues and pull requests are welcome.

## Ground rules

- **Clean-room originality.** Everything here is authored or generated from scratch.
  Do not paste third-party licensed code, copyrighted text, or any real client or
  brand name into the repo. Inspiration is fine; copying is not. Record any new
  script/data provenance in `references/PROVENANCE.md`.
- **Follow the authoring contracts.** Skills, scripts, and templates follow
  `references/ENGINE-CONTRACTS.md`: fixed `SKILL.md` section order, domain-qualified
  triggers, an acyclic dependency graph (orchestrator → specialist, never back),
  graceful degradation, and secrets via environment variables only.
- **The free path is the product.** Any skill that can use a paid MCP/API must also
  ship a real built-in/free path and detect the tool at runtime — see
  `references/CAPABILITY-TIERS.md`.
- **Standard library only** for Python scripts (no third-party packages). Each
  script runs as a CLI and imports as a library, defaults to JSON on stdout, and
  offers a `--human` ASCII view. Invoke bundled scripts from skills via
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/..."` so they resolve when installed.

## Before you open a PR

Run both gates from the repo root (use `py` instead of `python3` on Windows):

```text
python3 scripts/smoke_test.py        # expect "32/32 checks passed."
python3 scripts/verify_release.py    # expect every check PASS
```

Both must pass. The release gate also checks doc/version consistency, that every
`SKILL.md` script path resolves, `PROVENANCE.md` completeness, clean-room hygiene,
and that skill bodies invoke scripts via `${CLAUDE_PLUGIN_ROOT}`.

## Reporting issues

Open a GitHub issue. If a **Stable** skill does not do what its description says,
that is a bug — include the skill name, exactly what you ran, and what happened.
