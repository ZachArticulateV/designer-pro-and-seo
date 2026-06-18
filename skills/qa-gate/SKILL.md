---
name: qa-gate
description: Run a 9-phase pre-delivery QA and stress test on a build, producing PASS/CONDITIONAL/FAIL plus Risk Rating (Low/Med/High/Critical), Critical Issues, Warnings, Recommendations, Nice-to-Haves, Estimated Fix Time, and Client-Ready Status. Trigger when the user says "qa check", "is this ready to ship", "pre-delivery review", "client-ready check", "stress test the site", or before any client handoff.
---

# qa-gate

**Family:** build-and-qa
**Status:** Stable

## Purpose

The mandatory pre-delivery gate for any client-bound build. Walks the build
through 9 phases and produces a structured pass/fail report with a risk rating and
an explicit YES/NO client-ready verdict. This is the *gate*, not the *fix* — it
reports; remediation happens in the appropriate skills.

## Triggers

- "qa check" / "qa gate"
- "is this ready to ship" / "client-ready check"
- "pre-delivery review"
- "stress test the site"

## Inputs

- Build URL or local path
- Target client/audience
- Deployment target (Vercel, WordPress, GHL, etc.)
- Brief or original spec (for the completeness check)

## Steps

1. **Load the report template** `templates/qa-report-template.md`.
2. **Detect tooling.** Check whether the Playwright extension is available
   (see `extensions/playwright/`). If yes, use it for live phases; if no, run the
   static path and mark live-only checks `N/A — needs Playwright`.
3. **Run the 9 phases**, recording PASS / WARN / FAIL / N/A for each:
   1. **Functional** — forms submit, links resolve, no console JS errors.
   2. **Visual fidelity** — matches the design system; responsive at 375/768/1280;
      no broken layouts. (Playwright deepens this; `design-visual-qa` for diffs.)
   3. **Accessibility** — delegate to `design-accessibility` (axe + WCAG AA). Static
      fallback: check contrast, alt text, heading order, labels, focus visibility.
   4. **Performance** — Core Web Vitals (LCP < 2.5s, CLS < 0.1, INP < 200ms).
      Use `seo-google` (PSI/CrUX) if available; else flag for field verification.
   5. **Security** — HTTPS, security headers, no exposed secrets in source, audit
      third-party scripts.
   6. **Content completeness** — no lorem ipsum, no broken images, no placeholder
      copy; compare against the brief for missing pieces.
   7. **SEO baseline** — delegate to `seo-page` (title, meta, OG, schema, canonical).
   8. **Cross-device / browser** — sanity at key breakpoints/browsers.
   9. **Deployment readiness** — env vars set, redirects, analytics installed, DNS.
4. **Apply the verdict rule.** Any unresolved CRITICAL ⇒ OVERALL = FAIL and
   CLIENT-READY = NO. CONDITIONAL PASS only when remaining items are WARN or lower.
5. **Estimate fix time** and bucket findings into Critical / Warnings /
   Recommendations / Nice-to-haves.
6. **Render** the filled `qa-report-template.md`. Never declare client-ready with
   an open critical issue.

## Outputs

Structured QA Summary Report (from `templates/qa-report-template.md`): overall
status, risk rating, per-phase results, bucketed findings, estimated fix time, and
an explicit client-ready YES/NO.

## Dependencies

- `templates/qa-report-template.md` (required)
- `design-accessibility` (phase 3), `seo-page` (phase 7), `seo-google` (phase 4),
  `design-visual-qa` (phase 2/8) — all orchestrated one-directionally
- Playwright extension (optional — deepens phases 2/3/4/8; static path otherwise)

## Notes

This is the gate, not the fix. Remediation happens in `design-build`,
`seo-technical`, etc. Pairs with `blast-prompt` as the build bookend. Never skip
this gate when delivering to a paying client.
