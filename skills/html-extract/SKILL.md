---
name: html-extract
description: Pull structure, design tokens, and component patterns from a reference website into a clean, annotated inspiration file — for reimplementation from scratch, never verbatim reuse. Trigger when the user says "html extract", "scrape this site for reference", "I like how this site looks, use it as a reference", "pull the structure from", or "use this site as inspiration".
---

# html-extract

**Family:** build-and-qa
**Status:** Stable

## Purpose

Given a reference URL, extract the rendered structure, design tokens (fonts,
colors), and component patterns into a clean, annotated reference that downstream
skills (`design-build`, `parallel-build`, `blast-prompt`) use as *inspiration*.
This is pattern capture for reimplementation — **not** copy/paste of someone's
deployed code.

## Triggers

- "html extract" / "scrape this site for reference"
- "I like how X looks, pull it" / "use this site as inspiration"
- "give me the structure of" / "pull components from"

## Inputs

- Reference URL
- What to extract: full page | hero | nav | pricing | components-only
- Output location (defaults to the user's project workspace, e.g. `./inspiration/`)

## Steps

1. **Fetch the page** — static fetch (WebFetch / `curl`) for the free path; if it's
   JS-rendered and Playwright is available, render first. Say which path ran.
2. **Extract**: the HTML structure (section outline), the dominant color palette and
   font families, and the recurring component patterns (hero, nav, pricing,
   testimonials, footer).
3. **Clean**: strip analytics, ads, third-party scripts, and deploy-only IDs/classes
   — keep structure and tokens, drop the cruft.
4. **Annotate**: label each section with what it is and *why* it's worth borrowing
   (the pattern, not the pixels).
5. **Save** to the user's project workspace (e.g. `./inspiration/<slug>.md`) with the
   source URL + capture date in frontmatter, and a banner: **inspiration only — never
   deploy verbatim**.

## Outputs

- Annotated inspiration file (structure + token list + component catalog)
- Source attribution (URL + date) in the file's frontmatter

## Dependencies

- None required (static fetch). Optional: Playwright (JS-rendered sites)

## Notes

The legal/ethical line is firm: capture *patterns* to rebuild with the user's own
brand and content; the output is context for other skills, never deployable code.
Respect the source site's Terms of Service (see `PRIVACY.md`).
