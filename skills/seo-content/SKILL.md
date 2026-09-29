---
name: seo-content
description: Content quality and E-E-A-T analysis with AI-citation-readiness assessment. A deterministic eight-dimension audit (author / credentials / dates / sourcing / first-hand signals with a stricter YMYL bar, structure, readability, depth by page type, keyword placement, links, scaled-content tells like leaked template placeholders, passage citability) scores a page 0-100 with a fix per finding, then the skill judges what a script can't. Trigger when the user says "content quality", "E-E-A-T", "content analysis", "readability check", "thin content", "content audit", or "is this content good enough".
---

# seo-content

**Family:** seo
**Status:** Stable

## Purpose

Evaluate a piece of content for both human trust (E-E-A-T) and machine citability.
The dual framing matters in 2026: content must convince human reviewers *and* be the
kind of passage an LLM will quote.

## Triggers

- "content quality" / "content audit"
- "E-E-A-T" / "readability" / "thin content"
- "is this content good" / "AI citation readiness"

## Inputs

- Content URL or local markdown/text/HTML file
- Target audience and search intent
- Author / publication signals (if relevant)

## Steps

1. **Run the content audit** (HTML, Markdown or text; `--type` sets the depth floor;
   YMYL is auto-detected — force with `--ymyl yes|no`; `--as-of` enables staleness):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/content_audit.py" --file <file> --url <page URL> \
     --keyword "<primary topic>" --type article --as-of <YYYY-MM-DD> --human
   ```
   Eight dimensions, every finding with a fix, plus a 0-100 content score — rubric,
   thresholds and scoring in `references/seo-content/content-rubric.md`:
   - **E-E-A-T signals** — author (meta / schema / byline), credentials or expert
     review (required on YMYL), publish + updated dates and staleness, statistics
     without an outbound source, first-hand experience markers, About/Contact.
   - **Structure** — one H1, no heading-level skips, H2 sections on long content.
   - **Readability** — sentence length, very long sentences, walls of text, Flesch.
   - **Depth** — word count against the page type's floor; lists/tables on long pages.
   - **Keyword** — title / H1 / intro / subheading / meta / slug placement, stuffing.
   - **Links** — in-content internal links (nav/footer excluded), generic anchors.
   - **Originality** — leaked template placeholders (critical: a scaled-content tell),
     generic filler phrasing, duplicated sentences. Never labeled "AI-written".
   - **Citability** — passage citability via `geo_check.py` (same scorer as seo-geo).
2. **Judge what a script can't:** is the first-hand experience real, are the credentials
   relevant to the topic, is each claim *correct*, does the page answer the intent
   better than what already ranks? Read against `references/shared/eeat-criteria.md`.
3. **Fix the weak passages** listed under `citability` (the full list comes from
   `geo_check.py --content <file> --human`) so each leads with one specific, sourced
   claim.
4. **Render** the score, per-dimension findings grouped Critical → Info, and
   sentence-level revisions — label observable signals as such, never "Google's
   E-E-A-T score".

## Outputs

- Content score (0-100) with per-dimension counts and every finding's fix
- YMYL verdict and the raised-bar findings it triggers
- Sentence-level revision suggestions, including the weak-passage list

## Dependencies

- `scripts/seo/content_audit.py` (required) — the eight-dimension content audit
- `scripts/seo/geo_check.py` (required, imported) — passage citability scoring
- `references/seo-content/content-rubric.md` (required) — thresholds, YMYL bar, scoring
- `references/shared/eeat-criteria.md` (required) — the E-E-A-T concept the signals serve
- Related: `seo-geo` (AI-search depth), `seo-content-brief` (production counterpart),
  `content-draft` (writes the draft) — composed, not hard-depended (one-directional graph)

## Notes

This skill audits; `content-draft` produces and `seo-content-brief` plans. Citability
is now a first-class quality dimension, not a nice-to-have.
