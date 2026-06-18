---
name: seo-strategy
description: Strategic SEO planning by business type, combining an original evidence-led planning loop with industry-specific templates to produce a roadmap, content calendar, and prioritized investments. Trigger when the user says "seo strategy", "seo plan", "content strategy", "keyword strategy", "site architecture", "seo roadmap", or is planning multi-month SEO work.
---

# seo-strategy

**Family:** seo
**Status:** Stable

## Purpose

Strategic planning that merges two complementary approaches:

- **The Evidence Loop** (original methodology): **Map** the current baseline →
  **Prioritize** by impact × effort × intent → **Execute** the highest-leverage
  changes → **Measure** each against a defined outcome, then repeat.
- **Industry templates** — by business type (SaaS, e-commerce, local, publisher,
  agency), the shape the plan should take.

## Triggers

- "seo strategy" / "seo plan" / "seo roadmap"
- "content strategy" / "keyword strategy"
- "site architecture planning" / "evidence-led seo" / "long-term SEO plan"

## Inputs

- Domain and business type
- Time horizon (3 / 6 / 12 months)
- Current resources (in-house writer? agency budget?)
- Existing keyword baseline (or run `seo-cluster` first)

## Steps

1. **Map (baseline).** Pull what's known: current rankings/content/links/technical.
   Use `seo-audit` for a health snapshot and `seo-cluster` for the keyword universe
   when available; otherwise work from what the user provides.
2. **Apply the industry template** for the business type to set the plan's shape
   (e.g. local → GBP + location pages + reviews; SaaS → comparison + integration +
   use-case pages; publisher → topic clusters + freshness).
3. **Prioritize.** Score opportunities by impact × effort × search intent; sequence
   the highest-leverage first.
4. **Execute → Measure.** For each roadmap item, define the change *and* the metric
   that proves it worked (rankings, clicks, conversions, citations).
5. **Render** a multi-month roadmap (Gantt-style markdown), a content calendar, a
   prioritized investment list, and a measurement plan tied to each task.

## Outputs

- Roadmap (Gantt-style markdown) + content calendar
- Prioritized investment list
- Measurement plan (one metric per task)

## Dependencies

- Optional: `seo-cluster` (keyword grounding)

## Notes

The Evidence Loop keeps the plan honest — every task is tied to a measurable
outcome, not a vanity deliverable. Industry templates keep it concrete.

Related: Step 1 can pull a baseline from `seo-audit`. That is a prose reference, not
a `Dependencies` edge — `seo-audit` is the orchestrator, so listing it here would
create a back-edge in the graph.
