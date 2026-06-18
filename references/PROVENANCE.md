# PROVENANCE LEDGER (internal — clean-room record)

> **Purpose.** This is the originality audit trail for a plugin intended for
> **free public release on GitHub** under a hard constraint: *everything must be
> original and license-clean; other plugins are inspiration only, never copied.*
> A public repo makes this non-negotiable — no third-party licensed code, no
> copyrighted text, no real client/brand names may ship. Keep this ledger current
> as assets are added; it is the document you point to if anyone questions
> provenance. ("License: proprietary" below records *original authorship by us* —
> the repo's distribution license is set separately in `LICENSE`.)

## Clean-room rules (enforced for every asset)

1. **Inspiration, not transcription.** Reading another plugin to understand a
   *capability* is fine. Copying its files, prompt text, data rows, or wording
   is not — even "rewritten lightly."
2. **No third-party names in shipped/user-facing files.** Source attribution
   (if legitimately required, e.g. CC BY) lives in `NOTICE.md`, never in skill
   names, descriptions, README marketing, or `plugin.json`.
3. **Data is generated, not lifted.** CSV libraries are produced from first
   principles or from openly-licensed primary sources, with the method recorded
   below. Matching another product's exact row counts is treated as a red flag.
4. **Standards are referenced, not redistributed.** Implement against WCAG /
   Schema.org / CWV; do not paste their text.

## Asset ledger

| Asset | Status | Author | Source basis | License | Notes |
|---|---|---|---|---|---|
| 45 SKILL.md bodies | original | Zachary W. | written from scratch | proprietary | capabilities informed by general domain knowledge |
| `scripts/design/design_system.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; deterministic scoring engine |
| `scripts/design/gen_palettes.py` | BUILT | Zachary W. | written from scratch | proprietary | computes palettes via HSL + WCAG math; reproducible |
| `scripts/workflow/portable_html.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; path-traversal-guarded inliner |
| `scripts/workflow/csv_to_report.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; sensitive-column redaction |
| `scripts/smoke_test.py` | BUILT | Zachary W. | written from scratch | proprietary | install verification |
| `scripts/seo/schema_gen.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; Schema.org JSON-LD generate + validate vs Google rich-results required/recommended props; encodes the 2026 FAQPage rich-result deprecation (spec referenced, not redistributed) |
| `scripts/seo/sitemap_tools.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; sitemaps.org-compliant generate/validate; enforces the 50,000-URL / 50 MB protocol limits |
| `scripts/seo/tech_audit.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; single-page technical SEO checks; encodes CWV targets (INP<200ms) + AI-crawler robots policy from public standards |
| `scripts/seo/geo_check.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; GEO passage-citability scoring + llms.txt/robots checks; implemented against public GEO findings (no third-party text) |
| `scripts/seo/hreflang_tools.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; hreflang validate/generate against ISO 639-1 / ISO 3166-1 code sets |
| `scripts/seo/drift_tools.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; SEO baseline capture + diff with severity classification |
| `scripts/design/render_page.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; renders an accessible single-file HTML page from the engine spec (WCAG-aware, prefers-reduced-motion, focus-visible) |
| `scripts/design/tokens_emit.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; emits CSS / Tailwind / SCSS / Style-Dictionary tokens from the engine spec |
| `scripts/workflow/capability_probe.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; detects available CLIs/env for the capability-tier cascade; never emits secret values; Codex-reviewed |
| `scripts/verify_release.py` | BUILT | Zachary W. | written from scratch | proprietary | stdlib only; release-gate verifier (smoke + doc/provenance/clean-room/config consistency); Codex-reviewed |
| `templates/*.md` | BUILT | Zachary W. | written from scratch | proprietary | original framework wording |
| Evidence-led SEO methodology | original | Zachary W. | own loop + own prompts | proprietary | replaces third-party "FLOW" name/prompts |
| BLAST / 5-Dimensions framing | original content | Zachary W. | generic acronym, original sections | proprietary | rename if any TM concern surfaces |

### Per-CSV records (the `data/` libraries — built clean-room)

| File | Status | Rows | Method | Source / license |
|---|---|---|---|---|
| `color-palettes.csv` | BUILT (generated) | 24 | Produced by `gen_palettes.py` from 24 named industry/mood base hues via HSL rotation + WCAG contrast math. **Fully reproducible** — re-running the script reproduces the file byte-for-byte. | generated, proprietary |
| `ui-styles.csv` | BUILT (authored) | 18 | Enumerated from well-known, observable visual treatments; every characteristics/best-for/anti-pattern cell written for this plugin. | first-principles, proprietary |
| `font-pairings.csv` | BUILT (authored) | 22 | Pairings of openly-licensed Google Fonts with our own pairing rationale. No third-party pairing list used. | Google Fonts are OFL/Apache (referenced, not redistributed); rationale proprietary |
| `ux-rules.csv` | BUILT (authored) | 32 | Established usability principles restated in our own words with our own check/priority columns. | first-principles, proprietary |
| `product-types.csv` | BUILT (authored) | 26 | Product/page-type → default mappings authored from domain knowledge. | first-principles, proprietary |

> Row counts reflect what was actually built (deliberately **not** matched to any
> other product's counts). To verify the generated palette file is original and
> reproducible: `python3 scripts/design/gen_palettes.py --print` regenerates it
> from the algorithm in the script.

## Data clean-room method (when filling `data/`)

The design-intelligence CSVs must be **independently constructed**, not copied:

- **UI styles** — enumerate from observable, well-known visual treatments
  (each row authored with our own characteristics/fit/anti-pattern columns).
- **Color palettes** — generate programmatically (HSL/contrast math in our own
  script) and/or curate from openly-licensed palette sources with attribution;
  record the generator/seed in this ledger.
- **Font pairings** — built from Google Fonts metadata (open) with our own
  pairing rationale; no third-party pairing list copied.
- **UX rules / product-type mappings** — written in our own words from
  established usability principles (Nielsen heuristics et al. are ideas, not
  protected expression — but the wording here is ours).

Record, per CSV, the generation date, method, and any primary source + its
license. **Row counts should reflect what we actually built, not a target
borrowed from another product.**

## Removed provenance language (history)

For the record, the following were removed during the Phase 1 quarantine because
they named third-party plugins in user-facing or product files:

- `plugin.json` description previously listed several third-party plugins by name.
- `README.md` / `CLAUDE.md` previously referenced specific source plugins.
- `data/README.md` previously stated the first CSV batch came from another
  plugin's source folder and declared row counts matching that product exactly.

These are documented here (internal) and scrubbed from all shipping files.
