---
name: design-accessibility
description: Accessibility audit against WCAG 2.2 — structural checks (alt text, heading order, form labels, lang, focus order, contrast) on any HTML, plus a full axe-core scan when Playwright is installed. Produces a severity-ranked report with remediation. Trigger when the user says "accessibility", "a11y check", "wcag audit", "axe", "is this accessible", "screen reader check", or "keyboard nav".
---

# design-accessibility

**Family:** design
**Status:** Stable

## Purpose

A dedicated accessibility skill. Runs **structural WCAG 2.2 checks on any HTML with
no tools required** (the free path) and a **full axe-core scan when Playwright is
installed** (the deep path), producing a severity-ranked report that downstream
skills (`qa-gate`, `design-build`) can act on.

## Triggers

- "accessibility" / "a11y check" / "wcag audit"
- "axe scan" / "is this accessible"
- "screen reader check" / "keyboard nav check" / "contrast check"

## Inputs

- Target URL or local build path
- WCAG level: AA (default) | AAA
- Viewports to test (defaults: 375 / 768 / 1280)

## Steps

1. **Detect Playwright.** If available → deep path (step 3). If not → static path
   (step 2). Always say which path ran.
2. **Static WCAG checks** (free path, on the page source): images have meaningful
   or empty `alt`; one `<h1>` and logical heading order; form fields have
   associated `<label>`s; `<html lang>` is set; a skip-to-content link exists;
   viewport meta present; landmark/semantic elements used; document contrast
   expectations against the design tokens (`on_primary`, `text_on_bg_contrast`).
3. **Deep axe scan** (Playwright path): for each viewport, run axe-core; test
   keyboard nav (tab order, visible focus, focus traps in modals, escape routes);
   test `prefers-reduced-motion`; test 200% text scaling for truncation/overflow;
   verify computed-style color contrast.
4. **Classify** findings critical / serious / moderate / minor with the WCAG
   success criterion and remediation guidance (file:line when source is available).
5. **Render** the report; note clearly that the static path is a subset and a full
   axe scan needs Playwright.

## Outputs

- Severity-ranked accessibility report (WCAG 2.2), with per-issue remediation
- An explicit "static vs. full axe" coverage statement

## Dependencies

- None required for the static path (analyzes provided HTML)
- Optional: Playwright extension + `@axe-core/playwright` for the full automated scan

## Notes

Mandatory inside the `qa-gate` workflow (phase 3); also standalone. The static path
catches a real subset of WCAG issues, but only a browser-based axe scan covers
computed contrast and live keyboard behavior — the report says so rather than
implying full coverage.
