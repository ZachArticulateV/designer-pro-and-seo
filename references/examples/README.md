# Examples (golden outputs)

Worked examples for the shipping skills — used as golden references and by
`scripts/smoke_test.py`. Each is reproducible from the bundled inputs.

## design-system/
- `saas-landing.txt` — `design_system.py --human` output for a SaaS landing page
  (`--product-type saas-landing --industry saas --keywords "modern, trustworthy,
  minimal"`). Regenerate:
  ```
  python3 scripts/design/design_system.py --product-type saas-landing \
    --industry saas --keywords "modern, trustworthy, minimal" --human
  ```

## portable-html/
- `src/` — a tiny multi-file build (HTML + CSS + JS) used as the porter fixture.
  `scripts/smoke_test.py` ports it to every target and asserts the output is
  self-contained.

These outputs are deterministic — the same inputs reproduce them, which is part of
the provenance guarantee in `references/PROVENANCE.md`. The smoke test compares the
design-system golden (`saas-landing.txt`) exactly (after normalizing line endings),
so it is a live regression oracle, not just a sample.
