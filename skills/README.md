# skills/

**45 skills, one folder each.** Every `SKILL.md` follows the same fixed section order
(Purpose → Triggers → Inputs → Steps → Capability routing → Outputs → Dependencies →
Notes), declares its status, and names the bundled scripts it runs. **★ Core** skills are
3-layer: a deterministic engine, earned `references/`, and a golden example pinned by
tests. The other skills are Stable single-file skills. Claude picks a skill from its description
and trigger phrases, so you rarely call one by name.

## Design (10)

| Skill | What it does |
|---|---|
| ★ [`design-accessibility`](design-accessibility/SKILL.md) | Audits HTML against WCAG 2.2 — no-tools structural checks (alt text, heading order, form labels, lang, landmarks, skip link, viewport meta,… |
| ★ [`design-build`](design-build/SKILL.md) | Generate distinctive, production-grade frontend UI code from a design system — starting from an on-brand, accessible, rendered HTML scaffold and… |
| ★ [`design-cro`](design-cro/SKILL.md) | Run a heuristic conversion-rate-optimization review of a landing or funnel page — CTA hierarchy, above-fold weight, form friction, trust-signal… |
| [`design-dimensions`](design-dimensions/SKILL.md) | Build a design prompt structured around the 5 Core Dimensions — Pattern & Layout (skeleton), Style & Aesthetic (skin), Color & Theme (palette),… |
| ★ [`design-motion`](design-motion/SKILL.md) | Implement motion from a design system's motion tokens — emit real CSS/JS for entrance/scroll animations, micro-interactions (hover/press/focus),… |
| ★ [`design-research`](design-research/SKILL.md) | Run a competitive research pass on a target site and its top competitors, producing a structured competitive-intelligence report — brand snapshot,… |
| ★ [`design-system-gen`](design-system-gen/SKILL.md) | Generate a complete design system — pattern, style, color palette (with WCAG contrast), typography pairing, effects, anti-patterns, and a… |
| [`design-system-persist`](design-system-persist/SKILL.md) | Save a generated design system to disk as a hierarchical Master + per-page-overrides structure so future sessions can retrieve it for the project |
| [`design-tokens-emit`](design-tokens-emit/SKILL.md) | Convert a design system spec into code-deliverable token files — CSS variables, a Tailwind config fragment, SCSS variables, or Style-Dictionary JSON |
| ★ [`design-visual-qa`](design-visual-qa/SKILL.md) | Capture full-page screenshot baselines at multiple viewports and browsers, then diff later runs against them to catch unintended rendering changes |

## Build & QA (5)

| Skill | What it does |
|---|---|
| [`blast-prompt`](blast-prompt/SKILL.md) | Generate a complete build brief in BLAST format — Blueprint, Link, Architect, Stylize, Trigger — so a build agent can one-shot a high-quality build |
| [`html-extract`](html-extract/SKILL.md) | Capture a reference site's section structure, color and font tokens, and recurring component patterns into a clean, annotated inspiration file for… |
| ★ [`parallel-build`](parallel-build/SKILL.md) | Spin up multiple website or page variants in parallel — each in its own git worktree or sibling folder, built by a sub-agent from the same brief… |
| ★ [`portable-html-port`](portable-html-port/SKILL.md) | Port a built site or page into a single self-contained HTML file — CSS and JS inlined, small images base64-embedded, large ones flagged for CDN,… |
| ★ [`qa-gate`](qa-gate/SKILL.md) | Run a 9-phase pre-delivery QA gate on a build and return a PASS/CONDITIONAL/FAIL verdict with a risk rating (Low/Medium/High/Critical), bucketed… |

## SEO (23)

| Skill | What it does |
|---|---|
| ★ [`seo-audit`](seo-audit/SKILL.md) | Orchestrates a multi-specialist SEO audit — detects business type, dispatches the available specialist skills, and aggregates one weighted health… |
| [`seo-backlinks`](seo-backlinks/SKILL.md) | Backlink profile analysis — referring domains, anchor-text distribution, toxic-link flags, competitor link gap, and link-building targets |
| ★ [`seo-cluster`](seo-cluster/SKILL.md) | SERP-overlap semantic topic clustering for content architecture — groups keywords into hub-and-spoke clusters (one pillar + supporting spokes)… |
| [`seo-competitor-pages`](seo-competitor-pages/SKILL.md) | Generate SEO-optimized competitor comparison and alternatives pages — "X vs Y" layouts, "alternatives to X" pages, feature matrices, schema, and… |
| [`seo-content-brief`](seo-content-brief/SKILL.md) | Generate competitive SEO content briefs — per-section heading structure, word-count guidance anchored on top-ranking pages, required entities,… |
| ★ [`seo-content`](seo-content/SKILL.md) | Content quality and E-E-A-T analysis with AI-citation-readiness assessment |
| [`seo-dataforseo`](seo-dataforseo/SKILL.md) | Pulls live SERP, keyword, backlink, and AI-visibility data from the DataForSEO MCP when connected — search volume, keyword difficulty,… |
| ★ [`seo-drift`](seo-drift/SKILL.md) | Git-for-SEO — capture baselines of on-page SEO-critical elements and diff against them to catch regressions a deploy introduced (title changed,… |
| ★ [`seo-ecommerce`](seo-ecommerce/SKILL.md) | Optimizes e-commerce SEO across product and category pages — on-page product elements, Product schema validation, image SEO, and faceted/canonical… |
| [`seo-firecrawl`](seo-firecrawl/SKILL.md) | Site crawling, mapping, and JS-rendered scraping via the Firecrawl MCP when connected; otherwise builds a URL inventory from the sitemap and does… |
| ★ [`seo-geo`](seo-geo/SKILL.md) | Optimize content to be cited inline by AI answer engines — AI Overviews, ChatGPT, Perplexity, and Bing Copilot |
| [`seo-google`](seo-google/SKILL.md) | Pulls real Google field data — Search Console search analytics (impressions, clicks, CTR, position), URL Inspection and sitemap status, PageSpeed… |
| ★ [`seo-hreflang`](seo-hreflang/SKILL.md) | Validates and generates hreflang annotations for international SEO |
| ★ [`seo-image-audit`](seo-image-audit/SKILL.md) | Audit a page's images for SEO and performance — alt-text quality (missing, linked-empty, filename, stuffed, reused), modern formats (WebP/AVIF),… |
| [`seo-image-gen`](seo-image-gen/SKILL.md) | Generate SEO-ready images — OG/social previews, blog heroes, product shots, infographics, and favicons — at correct dimensions with SEO-aware… |
| ★ [`seo-local-unified`](seo-local-unified/SKILL.md) | Audits and optimizes local SEO — Google Business Profile, NAP consistency, citations, review velocity, and LocalBusiness schema |
| ★ [`seo-page`](seo-page/SKILL.md) | Single-URL SEO review — runs the technical audit and the content audit on one page (on-page elements, meta, E-E-A-T signals, readability, keyword… |
| [`seo-programmatic`](seo-programmatic/SKILL.md) | Programmatic SEO planning and safeguards for pages generated at scale — template design, URL patterns, internal-link automation, thin-content… |
| ★ [`seo-schema`](seo-schema/SKILL.md) | Detect, validate, and generate Schema.org structured data as JSON-LD |
| ★ [`seo-sitemap`](seo-sitemap/SKILL.md) | Audits and generates sitemaps.org-compliant XML sitemaps and the internal-link architecture around them |
| ★ [`seo-strategy`](seo-strategy/SKILL.md) | Plans multi-month SEO by business type — measures a baseline, diagnoses defects, maps the winnable topic territory, prioritizes by impact, effort,… |
| [`seo-sxo`](seo-sxo/SKILL.md) | Search Experience Optimization — reads the SERP backwards to detect page-type mismatches, then scores the target page against search-intent… |
| ★ [`seo-technical`](seo-technical/SKILL.md) | 10-dimension technical SEO audit with a fix per finding and a deterministic lab score — crawlability (RFC 9309 AI-crawler policy, redirects),… |

## Content & data (3)

| Skill | What it does |
|---|---|
| [`content-draft`](content-draft/SKILL.md) | Draft long-form content (blog post, service page, landing page, guide) from a brief or outline — structured, on-intent, and originality-checked,… |
| [`copywriting`](copywriting/SKILL.md) | Write conversion-focused copy for a page or section — headlines, subheads, value propositions, CTAs, feature/benefit blocks, and microcopy —… |
| [`csv-to-report`](csv-to-report/SKILL.md) | Convert a raw CSV into a structured, business-ready report using a 3-step framework — load + label, define rules, request structured deliverables |

## Business / GTM (1)

| Skill | What it does |
|---|---|
| [`client-outreach`](client-outreach/SKILL.md) | Generate cold-outreach openers, value-led follow-up sequences, niche-authority positioning, and a tool-import CSV with CAN-SPAM/GDPR/CASL… |

## Routing (three-brain hand-offs) (3)

| Skill | What it does |
|---|---|
| [`route-codex-review`](route-codex-review/SKILL.md) | Forced adversarial review pre-delivery — hands Claude-generated code, content, or plans to Codex (GPT-5.5) to find bugs, security risks, missing… |
| [`route-gemini-context`](route-gemini-context/SKILL.md) | Delegates large multi-file or whole-repo work to Gemini for architecture maps, refactor-impact analysis, and multi-document synthesis |
| [`route-three-brain`](route-three-brain/SKILL.md) | The routing law for handing off between Claude (primary driver), Codex/GPT-5.5 (adversarial review, second opinions), and Gemini (long-context,… |

## Adding or changing a skill

Follow `references/ENGINE-CONTRACTS.md` (section order, domain-qualified triggers,
one-way dependencies, a free path for every paid tool). Then update `SHIPPING.md`, the
skill's `**Status:**` line and `README.md` together. The release gate
(`scripts/verify_release.py`) fails if they drift apart.
