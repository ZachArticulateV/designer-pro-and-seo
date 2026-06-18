# scripts/

Shared executable helpers for skills in this plugin. Skills should call into here rather than embedding Python/Node in their SKILL.md bodies.

## Structure

- `seo/` — Python helpers for SEO skills: schema generation/validation, sitemap tools, single-page technical audit, GEO citability, hreflang, and SEO drift
- `design/` — design system reasoning engine, palette generation, page render, token emit
- `workflow/` — orchestrators/helpers for `parallel-build`, `qa-gate`, and `csv-to-report`

## Conventions

- Python: 3.10+ required; **standard library only** (no `requirements.txt` needed). If a dependency is ever required, declare it in a per-subfolder `requirements.txt`.
- Every script must work standalone (callable from CLI) and be importable as a library
- Idempotent by default — running a script twice with the same inputs produces the same output
- Outputs go to stdout (machine-readable JSON by default; `--human` flag for ASCII)

## Status

In use (all stdlib-only). Present:

- `design/`: `design_system.py`, `gen_palettes.py`, `render_page.py`, `tokens_emit.py`
- `seo/`: `schema_gen.py`, `sitemap_tools.py`, `tech_audit.py`, `geo_check.py`, `hreflang_tools.py`, `drift_tools.py`
- `workflow/`: `portable_html.py`, `csv_to_report.py`
- `smoke_test.py` (install verification)

Run `python3 scripts/smoke_test.py` (use `py` on Windows) to verify the install.
