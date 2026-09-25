# seo-drift severity model — how a captured change becomes a tier

Knowledge file for `seo-drift`. It explains *why* each on-page change lands in the tier
it does, so a reader can trust (and adjust) the verdicts `drift_compare.py` prints. It is
not a procedure — the steps live in `skills/seo-drift/SKILL.md`; the executable rules live
in `scripts/seo/drift_severity.py`.

## The one design rule: the model is derived from what we capture

The engine never invents a signal it cannot see. `scripts/seo/drift_tools.py` —
the canonical capturer — records exactly twelve fields per snapshot, plus a thirteenth
when a robots.txt is supplied (`--robots`):

```
url  title  meta_description  h1  canonical  meta_robots
og_title  og_description  og_image  schema_blocks  h2_count  word_count
[ai_crawler_verdict]   <- only with --robots; the shared ai_crawlers.py verdict
```

`url` is identity, not a signal, so it never produces a change. **Every other captured
field maps to exactly one numbered rule.** Add a field to `capture()` and you add a rule
here; remove one and its rule goes silent. That is the whole contract: the severity model
is a *function of the captured-element list*, authored from first principles against our
own list — no external comparison-rules source was consulted, and the rule count (15) is
incidental, not targeted at any outside number.

## The three tiers

A deliberately small model — three tiers, because the only decision a tier needs to drive
is *how fast must a human look*.

| Tier | The question it answers | Fix urgency |
|---|---|---|
| **critical** | Can this change remove the page from the index, or hand its ranking signals to a different URL? | Now — before anything else ships. |
| **high** | Did a *primary* relevance signal Google weights heavily change? | Same day — confirm it was intentional. |
| **advisory** | Did a *secondary* signal change, or one that is usually deliberate? | Review when convenient; often a no-op. |

`drift_compare.py` sorts changes critical → high → advisory (element name as the
deterministic tiebreak) and tallies a per-tier count, so the worst news is always first
and a deploy's blast radius is one glance.

## The rules (D1–D15)

### critical — de-indexing / signal-misrouting

| Code | Element | Fires when | Why critical |
|---|---|---|---|
| **D1** | `meta_robots` | a `noindex` directive is newly asserted | the page can drop out of the index entirely — the single most damaging silent change |
| **D2** | `meta_robots` | a `nofollow` directive is newly asserted | internal link equity stops flowing out of the page |
| **D3** | `canonical` | a present canonical now points to a *different* URL | ranking signals get reassigned to another page |
| **D4** | `canonical` | a present canonical is removed | the self-reference is lost; duplicate-content consolidation breaks |
| **D15** | `ai_crawler_verdict` | robots.txt newly blocks AI-search crawlers (`retrieval-blocked`) or a classic search engine (`search-engine-blocked`) | citation and AI Overview / AI Mode visibility disappear with no on-page change — the silent 2026 deploy failure |

`meta_robots` is tokenized (split on commas/whitespace, lowercased) and `none` is expanded
to its `noindex,nofollow` meaning, so a switch to `content="none"` still trips D1. Only a
*newly gained* directive is critical — losing a restriction is not (see D8).

### high — primary relevance signals

| Code | Element | Fires when | Why high |
|---|---|---|---|
| **D5** | `title` | the title tag changes or disappears | the strongest single on-page relevance signal |
| **D6** | `h1` | the H1 changes or disappears | the page's primary heading/topic signal |
| **D7** | `schema_blocks` | the JSON-LD block count *decreases* | structured data removed → rich-result eligibility lost |
| **D8** | `meta_robots` | robots changed but *no* noindex/nofollow was gained | a directive was lost or altered — serious, but not de-indexing |

### advisory — secondary signals and usually-intentional changes

| Code | Element | Fires when | Why advisory |
|---|---|---|---|
| **D9** | `meta_description` | the description changes | affects the SERP snippet, not ranking directly |
| **D10** | `canonical` | a canonical is *added* where none existed | usually an intentional self-canonical |
| **D11** | `schema_blocks` | the block count *increases* | new structured data — verify it validates, but rarely a regression |
| **D12** | `og_title` / `og_description` / `og_image` | any Open Graph value changes | social/share presentation only (one row per changed field) |
| **D13** | `h2_count` | the subsection count changes | structural shift worth noticing, not urgent |
| **D15** | `ai_crawler_verdict` | robots.txt moves to `retrieval-partial` (high) · or changes without reducing search/AI-search access, e.g. training bots newly blocked (advisory) | partial citation loss is serious; a training-policy change is usually deliberate |
| **D14** | `word_count` | body text moves **more than 20%** | content materially changed; within ±20% is editing noise and suppressed |

## The two thresholds, and why they exist

- **Word-count noise floor — 20% (`WORD_NOISE = 0.20`).** Re-rendered timestamps, a
  reworded sentence, a swapped widget all jitter the word count by a few percent. Flagging
  those would train the reader to ignore the report. 20% is the line between "someone
  edited a paragraph" and "a section is gone." Tune it per run with `--word-noise`.
- **Schema count direction matters.** A *drop* (D7) is high — lost rich results — while a
  *gain* (D11) is advisory. The same raw delta carries opposite risk depending on sign,
  which a flat "schema changed" rule would miss.

## What the model deliberately does *not* do

- **No fabricated magnitude.** The engine reports *that* an element changed and its tier;
  it never estimates traffic impact or a ranking-position delta from a single diff — that
  would be a synthesized number. Severity is a structural judgment, not a forecast.
- **One rule per element per run.** `meta_robots` yields at most one of D1/D2/D8, so a
  single element never double-counts and inflates the tally.
- **Intent is the human's call.** A critical verdict means "a human must confirm this was
  intended," not "this is a bug." A planned migration legitimately flips canonicals; the
  engine's job is to make sure that flip is never *silent*.
