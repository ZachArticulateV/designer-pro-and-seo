---
name: seo-cluster
description: Semantic topic clustering for content architecture — groups keywords into hub-and-spoke clusters with internal-link matrices. Free path groups by search intent; the premium path clusters by actual Google SERP overlap when DataForSEO is connected. Trigger when the user says "topic cluster", "content cluster", "semantic clustering", "pillar page", "hub and spoke", "content architecture", "keyword grouping", or "cluster plan".
---

# seo-cluster

**Family:** seo
**Status:** Stable

## Purpose

Plan content architecture as hub-and-spoke clusters: one pillar page per cluster,
supporting articles linking to/from it, with an internal-link matrix specifying
anchor text. Two tiers:

- **Free path** — group keywords by **search intent + semantic theme** (intent
  type, modifiers, the job the searcher is doing).
- **Premium path (differentiator)** — when DataForSEO is connected, cluster by
  **actual Google SERP overlap**: if two keywords share top-10 results, Google
  treats them as the same topic. This is the only similarity that truly matters,
  and the free path approximates it.

## Triggers

- "topic cluster" / "content cluster" / "semantic clustering"
- "pillar page" / "hub and spoke" / "content architecture"
- "keyword grouping" / "cluster plan"

## Inputs

- Seed keywords (or a single seed to expand)
- Cluster-size target; region / language

## Steps

1. **Expand seeds** into a keyword set (modifiers, questions, related terms).
2. **Cluster:**
   - Free path: group by intent (informational / commercial / transactional /
     navigational) and shared theme; flag where SERP-overlap data would refine it.
   - Premium path: if DataForSEO is present, fetch SERPs and cluster by top-10
     overlap (the accurate method).
3. **Assign roles** — one pillar (broad, high-intent) + spokes (specific) per cluster.
4. **Build the internal-link matrix** — every spoke links up to the pillar and to
   2–3 sibling spokes, with specific anchor text per link.
5. **Render** the cluster map, a hub-and-spoke document, and the link matrix (CSV/
   markdown). Hand pillars/spokes to `seo-content-brief` to brief each page.

## Outputs

- Cluster map (which keywords → which cluster, pillar vs spoke)
- Hub-and-spoke architecture document
- Internal-link matrix (anchor text per link)

## Dependencies

- None required (free intent-based path)
- Optional: DataForSEO (SERP-overlap clustering — the accurate method);
  `seo-content-brief` (brief each page)

## Notes

Be explicit about which tier ran: the free path groups by intent (a strong
approximation); true SERP-overlap clustering needs DataForSEO. Embedding-only
clustering is deliberately avoided — it produces clusters Google doesn't recognize.
