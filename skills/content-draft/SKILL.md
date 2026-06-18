---
name: content-draft
description: Draft long-form content (blog post, service page, landing page, guide) from a brief or outline — structured, on-intent, and originality-checked, ready for human edit. Trigger when the user says "draft this", "write the blog post", "write the page", "turn this brief into content", "first draft", or has an outline/brief and needs the actual content written.
---

# content-draft

**Family:** content-and-data
**Status:** Stable

## Purpose

Turn a brief or outline into an actual first draft — the production counterpart to
the analysis skills. Fills the hole between `seo-content-brief` (which plans) and
`seo-content` (which audits): neither writes the content. This does, on-intent and
structured for both human readers and AI-search citability.

## Triggers

- "draft this" / "first draft"
- "write the blog post" / "write the page" / "write this guide"
- "turn this brief into content"

## Inputs

- A brief or outline (from `seo-content-brief`, or pasted) — or just a topic +
  target keyword + intent
- Audience and search intent
- Tone / brand voice (or pull from a design system)
- Target length / section structure

## Steps

1. **Confirm intent and structure.** Restate the search intent and the section
   outline (use the brief's per-section word counts if available).
2. **Draft section by section.** Open with a direct answer to the query (good for
   readers and AI Overviews), then develop each section. Make each paragraph one
   clear, source-able claim.
3. **Weave keywords naturally** — primary in title/H1/intro, related terms across
   sections; never stuff.
4. **Add structure for citability** — descriptive H2/H3s, lists/tables where they
   aid scanning, a short TL;DR, and FAQ where intent is question-led.
5. **Originality + accuracy pass.** Remove generic-AI phrasing; mark any factual
   claim that needs a source with `[cite]` so the human editor can verify.
6. **Hand off** to `seo-content` (E-E-A-T audit) and `seo-page` (on-page checks)
   before publishing. Always label output as a first draft for human edit.

## Outputs

- A structured first draft matching the brief
- `[cite]` markers on claims that need verification
- A short list of what a human editor should confirm (facts, brand specifics)

## Dependencies

- None required (pure method). Composes with `seo-content-brief` (upstream),
  `seo-content` + `seo-page` (downstream review).

## Notes

This produces a **first draft, not final copy** — it explicitly flags claims to
verify and is meant to be edited by a human with subject-matter knowledge. That
caveat protects against publishing unverified AI text (an E-E-A-T and trust risk).
