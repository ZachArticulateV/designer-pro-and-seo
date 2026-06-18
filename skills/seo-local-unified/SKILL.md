---
name: seo-local-unified
description: Unified local SEO — GBP optimization, NAP consistency, citations, reviews, and LocalBusiness schema (free strategy path), plus optional maps intelligence (geo-grid tracking, GBP API, Share of Local Voice) when DataForSEO/Places are connected. Trigger when the user says "local SEO", "Google Business Profile", "GBP", "map pack", "local pack", "citations", "NAP consistency", "local rankings", "service area", "multi-location", "geo-grid", "rank tracking", "review velocity", or "Share of Local Voice".
---

# seo-local-unified

**Family:** seo
**Status:** Stable

## Purpose

The complete local SEO surface in one skill. Combines local strategy (GBP, NAP,
citations, reviews, schema) with maps intelligence (geo-grid tracking, GBP API,
SoLV) because they operate together. The **free path covers strategy + schema +
NAP**; the **intelligence layer is optional** (DataForSEO / Google Places).

## Triggers

- "local seo" / "local rankings" / "map pack" / "local pack"
- "google business profile" / "gbp" / "citations" / "nap consistency"
- "service area" / "multi-location"
- "geo-grid" / "rank tracking" / "review velocity" / "share of local voice" / "solv"

## Inputs

- Business name + primary address; service area or location set
- Vertical / industry
- Data tier: free (strategy+schema) | DataForSEO | DataForSEO + Google Places

## Steps

1. **GBP optimization** (free): category selection, services, attributes,
   description, photos, posts cadence, Q&A.
2. **NAP consistency** (free): confirm the exact same Name/Address/Phone format
   across the site, GBP, and major directories; build a NAP matrix of the citations
   the user lists and flag mismatches (the silent local-ranking killer).
3. **Citations & reviews** (free): identify the priority directories for the vertical;
   set a review-velocity + response plan (don't gate/buy reviews — policy risk).
4. **LocalBusiness schema** via `seo-schema`: `name` + `address` required; add
   `telephone`, `geo`, `openingHoursSpecification`; multi-location → per-location
   pages each with its own schema and a clean URL.
5. **Intelligence (optional).** If DataForSEO/Places are configured: geo-grid rank
   tracking across a coordinate grid, GBP profile audit via API, cross-platform NAP
   verification, competitor radius map, and Share of Local Voice. If not, say what
   each would add.
6. **Render** a unified local report: strategy actions, NAP matrix, schema, and
   (when available) the intelligence visuals.

## Outputs

- Unified local SEO report + prioritized actions
- NAP consistency matrix + LocalBusiness schema
- Geo-grid / SoLV / competitor-radius visuals (when DataForSEO/Places present)

## Dependencies

- `seo-schema` (LocalBusiness schema) — required for the schema step
- Optional: DataForSEO (intelligence), Google Places API (max coverage)

## Notes

Strategy and intelligence are inseparable in practice, hence the unified skill. The
free path delivers a complete local strategy; intelligence deepens measurement.
Never buy or gate reviews — it's a Google policy violation.
