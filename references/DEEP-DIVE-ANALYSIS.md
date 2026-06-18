# Deep-Dive Analysis & Roadmap (archived)

> **Superseded (2026-06-16).** The project is now a **free, MIT-licensed** plugin
> released publicly on GitHub — not a product for sale. References below to "paid
> product", "for sale", or "buyers" are historical context from the v0.2.0 era and
> no longer reflect the project's direction. Kept for provenance only.

Recorded 2026-06-02. The analysis that drove the v0.2.0 build. Method: Claude
(driver) + Gemini 2.5 (whole-folder structural pass) + Codex/GPT-5.5 (adversarial
review of both the plan and the code).

## Starting state (v0.1.0)

An honest, well-organized **scaffold** — but 0% functional:
- All 41 skills were stubs (`Steps: TBD`, `Status: scaffold — body TBD`).
- All support dirs (`scripts/`, `data/`, `templates/`, `references/`, `extensions/`)
  held only README placeholders. Every referenced script/CSV/template was absent.
- Public docs named third-party plugins; the planned data layer mirrored another
  plugin's exact row counts — a licensing risk for a paid product.

## The three biggest risks for sale (all addressed)

1. **Empty product with concrete capability claims** — descriptions promised
   capabilities the empty bodies couldn't deliver (false-advertising / refund risk).
2. **Licensing / provenance** — competitor names in shipping files; data plan
   derived from another plugin. (User's hard constraint: original & license-clean.)
3. **Not self-contained / no free path** — paid-API dependence with no graceful
   degradation for the majority of buyers who won't have those APIs.

## Key judgment calls (where the models disagreed)

- **Merge vs. keep:** Gemini suggested merging seo-page→seo-audit, content+brief,
  system-gen+dimensions. Codex argued keep-separate (simple entry points sell).
  **Resolution:** share engines, keep separate user-facing skills.
- **Broaden vs. narrow:** Gemini listed many coverage gaps; Codex warned most are
  premature scope creep. **Resolution:** depth-first — build a small real core,
  add only Tier A (copywriting, content drafting, motion) that fills the *named*
  scope; defer the rest.
- **Split:** both agreed to split `seo-images-unified` (audit vs. gen have
  different legal/API risk). Done.

## Roadmap (executed in v0.2.0)

0. Sale hold (no public sale of TBD bodies with concrete claims).
1. Legal & provenance quarantine.
2. Cut public surface (12 Stable, rest marked In development).
3. Interface design + cross-cutting polish (ENGINE-CONTRACTS, triggers, the one
   real circular dep, conventions).
4. Build the clean vertical slice (engine + clean-room data + templates + 6 MVP
   bodies + MCP configs).
5. Beta hardening (smoke test, golden examples, QUICKSTART + compatibility matrix).
6. Expand by proven hubs (design-system-persist, csv-to-report → Stable).
7. Broaden (Tier A) + the image split.
   Final: Codex code review → fixed path-traversal, secret redaction, weak-match
   honesty, palette contrast, two over-claims; re-verified.

## What remains (future versions)

- Promote the 33 In-development skills to Stable in hub order, each with a real
  body, graceful degradation, and verification.
- Replace the placeholder `LICENSE` with a final EULA (legal review).
- Deferred coverage (Tier B/C): deployment automation, analytics depth, privacy/
  consent, video/podcast SEO, A/B testing, CRM/CMS-native — only after the core
  proves out, to avoid re-becoming a stub bundle.
