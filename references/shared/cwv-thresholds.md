# Core Web Vitals — Thresholds & Measurement

Shared knowledge for every skill that reasons about page performance
(`seo-technical`, `seo-google`, `seo-page`, `qa-gate`, `design-visual-qa`).
Knowledge, not steps — the procedure lives in the skills; this file fixes the
numbers and the concepts so they are stated once and cited everywhere.

## The three Core Web Vitals

Google's Core Web Vitals are a small, stable set of user-centric metrics, each
covering one facet of the loading experience. A page is judged on the **75th
percentile** of real visits (mobile and desktop scored separately).

| Metric | Measures | Good | Needs improvement | Poor |
|---|---|---|---|---|
| **LCP** — Largest Contentful Paint | Loading: when the largest visible element renders | **< 2.5 s** | 2.5 s – 4.0 s | > 4.0 s |
| **CLS** — Cumulative Layout Shift | Visual stability: unexpected movement of content | **< 0.1** | 0.1 – 0.25 | > 0.25 |
| **INP** — Interaction to Next Paint | Responsiveness: latency across all interactions | **< 200 ms** | 200 ms – 500 ms | > 500 ms |

A page "passes Core Web Vitals" only when **all three** metrics are in the Good
band at the 75th percentile. One Poor metric fails the set.

## INP replaced FID

Interaction to Next Paint (INP) is the responsiveness metric. It supersedes the
older First Input Delay (FID) — retired as a Core Web Vital in March 2024 —, because INP observes the latency of **every**
interaction during the visit (not just the first) and reports a high-percentile
worst case, making it a stricter and more representative signal.

## Field data vs lab data — they answer different questions

- **Field data (RUM):** real users' measurements, aggregated over a trailing
  window. This is what the Core Web Vitals *assessment* uses. It is the source of
  truth for whether a page passes. It can be sparse or absent for low-traffic
  URLs.
- **Lab data (synthetic):** a single scripted load in a controlled environment.
  Reproducible and good for debugging a regression, but it cannot measure INP
  directly (no real interactions) and will not match field numbers.

Rule of thumb: **diagnose in the lab, judge in the field.** Never present a lab
number as if it were the field assessment.

### Supporting / diagnostic metrics (not CWV themselves)

- **TTFB** — Time to First Byte: server + network latency before any byte
  arrives; a large TTFB caps how good LCP can be.
- **FCP** — First Contentful Paint: when *any* content first paints; an early
  milestone on the way to LCP.
- **TBT** — Total Blocking Time: main-thread blocking in the lab; a useful lab
  proxy for the responsiveness that INP measures in the field.

## What moves each metric (cause → lever)

- **LCP:** slow server (TTFB), render-blocking CSS/JS, late-loading hero image,
  unoptimized image bytes, missing image priority. Levers: faster origin/CDN,
  preload the LCP resource, compress and right-size the hero, defer non-critical
  script.
- **CLS:** images/iframes without width/height, injected banners or ads pushing
  content, web fonts swapping in at a different size, dynamic content above the
  fold. Levers: reserve space with explicit dimensions or `aspect-ratio`, avoid
  inserting content above existing content, use `font-display` carefully.
- **INP:** long JavaScript tasks blocking the main thread during a click/tap/key,
  heavy event handlers, large hydration costs. Levers: break up long tasks, defer
  or remove non-essential JS, yield to the main thread, reduce handler work.

## How the plugin reasons about CWV without a paid tool (free-path note)

The free Tier-2 path does **not** fabricate field numbers. When no CrUX/PSI key
is present, the plugin computes **lab-side heuristics** against the thresholds
above and labels them as lab estimates, emitting a `needs_tier1` flag for the
authoritative field assessment. A synthesized field number is on the
never-fabricate list. The key-absent lab path is a complete, honest deliverable;
a connected field source only deepens it.
