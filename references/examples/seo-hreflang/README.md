# Golden example — seo-hreflang (Tier-2: `hreflang_tools.py --cluster`)

Proves the free, offline cross-page hreflang audit. Return links, code agreement,
x-default consistency and `<html lang>` agreement are checked across a whole cluster,
not one page at a time.

## Input

`en.html`, `fr.html` and `de.html` form a three-locale cluster (fictional brand), and
`manifest.json` maps each URL to its file. Seeded defects:

- `/fr/` has no x-default.
- `/de/` doesn't link back to `/fr/`.
- `/de/` declares itself `de-de` but carries `<html lang="en">`.
- `/de/` points x-default at itself while `/` points it at `/`.
- `/de/` lists an `en-uk` alternate.

## Command

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/hreflang_tools.py" --cluster references/examples/seo-hreflang/manifest.json
```

The same result comes from passing the three HTML files, because each carries its
canonical.

## Expected free deliverable (Tier 2)

`"score": 68`, `"ok": false`:

- `H7` (high): no return link, `/de/` does not point back to `/fr/`
- `H2` (high): invalid code `en-uk` (use `GB`)
- `H4` (medium): `/fr/` has no x-default
- `H9` (medium): `de-de` disagrees with `<html lang="en">`
- `H12` (medium): two different x-default targets
- `H6` (info): `/uk/` is outside the audited set

The rules are in `references/seo-hreflang/cluster-rules.md`, and
`tests/test_hreflang_commerce.py` pins the result.
