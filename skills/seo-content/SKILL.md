---
name: seo-content
description: Content quality and E-E-A-T analysis with AI-citation-readiness assessment. Evaluates whether content will be trusted by human reviewers and cited by AI search (AI Overviews, ChatGPT, Perplexity). Trigger when the user says "content quality", "E-E-A-T", "content analysis", "readability check", "thin content", "content audit", or "is this content good enough".
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

1. **E-E-A-T** — Experience, Expertise, Authoritativeness, Trustworthiness (per
   Google's Quality Rater Guidelines): is there first-hand experience, a credentialed
   author, citations to primary sources, and clear sourcing?
2. **AI-citability (run the scorer):**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/geo_check.py" --content <file> --human
   ```
   It scores what fraction of passages make a specific, verifiable claim and stand
   alone when quoted — the strongest GEO signals. Fix the weak passages it lists.
3. **Readability** — sentence variety, jargon density, scannability (descriptive
   subheads, lists/tables where they aid comprehension).
4. **Thin-content / depth** — word count vs topical depth; missing sub-topics a
   competitor or the query implies.
5. **Originality** — strip generic-AI phrasing; flag claims needing a source.
6. **Render** per-dimension scores with sentence-level revision suggestions.

## Outputs

- Per-dimension scores (E-E-A-T, citability %, readability, depth, originality)
- Specific revision suggestions, including the weak-passage list from `geo_check.py`

## Dependencies

- `scripts/seo/geo_check.py` (citability scoring) — Python 3.10+, standard library only
- Related: `seo-geo` (AI-search depth), `seo-content-brief` (production counterpart),
  `content-draft` (writes the draft) — composed, not hard-depended (one-directional graph)

## Notes

This skill audits; `content-draft` produces and `seo-content-brief` plans. Citability
is now a first-class quality dimension, not a nice-to-have.
