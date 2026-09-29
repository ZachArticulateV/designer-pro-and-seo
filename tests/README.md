# tests/

**636 standard-library `unittest` cases**, runnable with plain Python or pytest. No
network (fetchers are exercised only on their SSRF refusal paths), no keys, no pip
installs beyond pytest if you prefer it. CI runs the suite on Ubuntu and Windows, on
Python 3.10 and 3.13 (`.github/workflows/verify.yml`).

```text
python3 -m unittest discover -s tests        # stdlib runner
python3 -m pytest -q                         # or pytest, if installed
```

## What each group pins

| Area | Test files |
|---|---|
| SEO engines | `test_tech_audit`, `test_content_audit`, `test_schema_gen`, `test_sitemap_linkgraph`, `test_image_audit`, `test_hreflang_commerce`, `test_ai_crawlers`, `test_ai_visibility`, `test_geo_scorecard`, `test_serp_cluster`, `test_local_maps`, `test_drift_engine`, `test_site_map`, `test_page_fetch` |
| Orchestrators | `test_site_audit` (one-command SEO health score), `test_design_qa` (qa_gate, CRO, motion), `test_audit_math` (re-normalized fan-in) |
| Design engine | `test_match`, `test_palette_slots`, `test_gen_charts`, `test_a11y_static`, `test_design_flagship_refs`, `test_design_research_flagship` |
| Safety | `test_net_safety`, `test_seo_fetchers_ssrf` (SSRF guard on every fetcher), `test_pii_boundary`, `test_cost_guard`, `test_capability_probe` |
| Repo contracts | `test_agents`, `test_agents_md`, `test_dag`, `test_handoffs`, `test_tier2_present`, `test_status_truth`, `test_refs_resolve`, `test_provenance`, `test_cleanroom_guard`, `test_stdlib_guard` |

## Conventions

- **Golden examples are pinned.** Every worked example under `references/examples/`
  has a test that asserts its exact score and finding codes. If you change a
  threshold, update the example's README and the test in the same commit.
- **One signal per case.** Fixtures are minimal HTML/CSS/robots strings built inside
  the test, so a failure points at one rule.
- **Deterministic.** Date-dependent checks take an explicit `as_of`, and no test reads
  the wall clock or the network.

`fixtures/` holds the few shared inputs (a robots.txt policy, ranker baselines).
