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

## Submitting a change (fork → pull request)

1. **Fork** this repo (the **Fork** button, top-right) — you get a copy under your account.
2. **Clone your fork** and enter it:
   ```
   git clone https://github.com/YOUR-USERNAME/designer-pro-and-seo
   cd designer-pro-and-seo
   ```
3. **Create a branch** (don't work on `main`):
   ```
   git checkout -b my-change
   ```
4. **Make your change**, following the ground rules above.
5. **Run both gates** (see below) — they must pass.
6. **Commit and push to your fork:**
   ```
   git add -A && git commit -m "Describe the change"
   git push origin my-change
   ```
7. **Open a pull request** against `ZachArticulateV/designer-pro-and-seo` `main` —
   GitHub shows a "Compare & pull request" button after you push. Say what changed and why.

For a one-line doc fix you can skip the terminal entirely: click the ✏️ pencil on any
file here and GitHub will fork + open the PR for you. For anything larger, open an issue
first so we can align before you build.

## Before you open a PR

Run both gates from the repo root (use `py` instead of `python3` on Windows):

```text
python3 scripts/smoke_test.py        # expect "37/37 checks passed."
python3 scripts/verify_release.py    # expect every check PASS
```

Both must pass. The release gate also checks doc/version consistency, that every
`SKILL.md` script path resolves, `PROVENANCE.md` completeness, clean-room hygiene,
and that skill bodies invoke scripts via `${CLAUDE_PLUGIN_ROOT}`.

## Reporting issues

Open a GitHub issue. If a **Stable** skill does not do what its description says,
that is a bug — include the skill name, exactly what you ran, and what happened.
