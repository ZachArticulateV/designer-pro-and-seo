# Golden example — seo-content / seo-page (Tier-2: `content_audit.py`)

Proves the free, offline content-quality path: a deterministic E-E-A-T-signal,
structure, readability, depth, keyword, link, originality and citability audit. No
key, no network, no LLM judgement in the loop.

## Input

`sample-article.html` is a short recovery-and-sleep article for a fictional treatment
center, so it is a **YMYL** page. It is seeded with realistic defects:
- no author and no clinical reviewer
- no publish date
- two uncited statistics
- a `[city]` placeholder leaked from a template
- filler phrasing ("in today's fast-paced world", "delve into", …)
- an H1→H3 heading skip
- a "Click here" anchor
- no About/Contact link

## Command

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/content_audit.py" \
  --file references/examples/seo-content/sample-article.html \
  --url https://example.test/blog/sleep-and-recovery \
  --keyword "sleep and recovery" --as-of 2026-09-25 --human
```

## Expected free deliverable (Tier 2)

Header: `(html, article, 144 words, YMYL)  score 13/100`. Then:

- `[CRITICAL] (originality) Template placeholder leaked into content: '[city]'`
- `[HIGH] (eeat) No identifiable author …`
- `[HIGH] (eeat) YMYL page shows no credentials or expert review`
- `[HIGH] (depth) 144 words -- thin for an article page (floor 300)`
- 8 `[MEDIUM]` findings: publish date, unsourced statistics, About/Contact, heading
  skip, keyword placement, generic anchor, filler phrasing, citability 25%
- `[INFO]` lines: YMYL detected, H2 count, Flesch reading ease, link counts

Every non-info finding carries a `fix:` line. The scoring arithmetic is in
`references/seo-content/content-rubric.md`.
