---
name: seo-sxo
description: Search Experience Optimization — reads the SERP backwards to detect page-type mismatches, derives user stories from intent signals, and scores a page from multiple persona perspectives to explain why a well-optimized page fails to rank. Trigger when the user says "SXO", "search experience", "page type mismatch", "SERP analysis", "user story", "persona scoring", "why isn't my page ranking", "intent mismatch", or "wireframe".
---

# seo-sxo

**Family:** seo
**Status:** Stable

## Purpose

When a page is technically clean, well-linked, and on-topic but still won't rank,
the cause is usually a **search-experience mismatch**: Google rewards one page type
for the query and you shipped another. This skill diagnoses that by working
backwards from the SERP. Free path: analyze the competitor pages currently ranking
(which you provide or fetch); the optional DataForSEO path auto-pulls the SERP.

## Triggers

- "SXO" / "search experience" / "intent mismatch"
- "page type mismatch" / "SERP analysis"
- "user story" / "persona scoring" / "wireframe for ranking"
- "why isn't my page ranking"

## Inputs

- Target URL and target keyword(s)
- The current top-ranking URLs (provided) — or DataForSEO to fetch the SERP
- Personas (optional — defaults to buyer / researcher / comparison shopper)

## Steps

1. **Get the SERP.** Use the top-ranking URLs the user provides (free path) or fetch
   via DataForSEO. Fetch each ranking page.
2. **Classify the rewarded page type** — what is Google ranking: review / comparison
   / how-to guide / product / category / video / tool / calculator?
3. **Classify the target page** the same way.
4. **Mismatch detection** — if the target type ≠ the rewarded type, that's the
   diagnosis ("Google rewards comparison pages; you shipped a blog post").
5. **Persona scoring** — score the target page from each persona's question: does it
   answer the buyer's, the researcher's, the comparison shopper's intent?
6. **Prescribe.** If mismatched, produce a wireframe + a `seo-content-brief` for the
   correct page type; if matched, the issue is elsewhere (authority/links) — say so.

## Outputs

- SERP page-type breakdown (what's rewarded)
- Mismatch report (rewarded type vs. your type)
- Per-persona scores
- A wireframe + content brief for the correct page type (when mismatched)

## Dependencies

- None required (free path uses provided ranking URLs)
- Optional: DataForSEO (auto-SERP); `seo-content-brief` (brief the corrected page)

## Notes

The "Google rewards X, you shipped Y" diagnosis is uniquely valuable — it asks
whether you're optimizing the wrong thing, not just how to optimize it.
