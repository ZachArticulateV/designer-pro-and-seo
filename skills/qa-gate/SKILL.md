---
name: qa-gate
description: Run a 9-phase pre-delivery QA gate on a build and return a PASS/CONDITIONAL/FAIL verdict with a risk rating (Low/Medium/High/Critical), bucketed findings (critical issues, warnings, recommendations, nice-to-haves), an estimated fix time, and an explicit client-ready YES/NO. Uses the Playwright extension when connected for live functional, visual, and performance checks; otherwise runs the static path and marks live-only checks N/A. Trigger when the user says "qa check", "qa gate", "is this ready to ship", "client-ready check", "pre-delivery review", or "stress test the site".
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
2. **Run the static gate in one command** — it drives the plugin's own engines
   (`a11y_static`, `tech_audit`, `image_audit`, `content_audit`, `schema_gen`,
   `link_graph`) over every page of the build, adds the exposed-secret scan and the
   deployment checks (staging `Disallow: /` left on, robots/sitemap/404/favicon,
   analytics), merges repeats across pages, applies the verdict rule, and fills the
   template:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/qa_gate.py" --dir dist/ --base-url https://client.example --project "<client>" --report
   ```
   (`--file page.html --url <URL>` for a single page; JSON without `--report`.)
   Then **detect tooling**: if the Playwright extension is available (see
   `extensions/playwright/`), deepen the live phases below; if not, the static report
   already marks them `N/A — needs Playwright`.
3. **Run the 9 phases**, recording PASS / WARN / FAIL / N/A for each:
   1. **Functional** — forms submit, links resolve, no console JS errors.
   2. **Visual fidelity** — matches the design system; responsive at 375/768/1280;
      no broken layouts. (Playwright deepens this; `design-visual-qa` for diffs.)
   3. **Accessibility** — dispatch the `design-accessibility` agent (axe + WCAG AA
      when Playwright is connected; else its bundled `a11y_static.py` structural
      checks — contrast, alt text, heading order, labels, focus visibility).
   4. **Performance** — Core Web Vitals (LCP < 2.5s, CLS < 0.1, INP < 200ms).
      Dispatch the `seo-google` agent for PSI/CrUX field data when a key/MCP is
      connected (the free PSI/CrUX key is preferred; any paid call routes through
      `cost_guard.py`, which fails open to the free path); else flag CWV for field
      verification.
   5. **Security** — HTTPS, security headers, no exposed secrets in source, audit
      third-party scripts.
   6. **Content completeness** — no lorem ipsum, no broken images, no placeholder
      copy; compare against the brief for missing pieces.
   7. **SEO baseline** — dispatch the `seo-page` agent (title, meta, OG, schema,
      canonical, images, internal links) as a real fan-out, not a prose handoff.
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
- `scripts/workflow/qa_gate.py` (required) — the static 9-phase runner (imports the SEO,
  content, image, schema, link-graph and a11y engines)
- `design-accessibility` (optional — adds axe/WCAG delegation; free path: static contrast/alt/heading/label/focus checks) — phase 3
- `seo-page` (optional — adds full on-page SEO pass; free path: inline title/meta/OG/canonical check) — phase 7
- `seo-google` (optional — adds PSI/CrUX field data; free path: flag CWV for field verification) — phase 4
- `design-visual-qa` (optional — adds screenshot diffs; free path: manual visual review) — phase 2/8
- Playwright extension (optional — deepens phases 2/3/4/8; static path otherwise)

## Notes

This is the gate, not the fix. Remediation happens in `design-build`,
`seo-technical`, etc. Pairs with `blast-prompt` as the build bookend. Never skip
this gate when delivering to a paying client.
