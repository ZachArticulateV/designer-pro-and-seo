# GEO scorecard — weighting rationale, passage rubric, crawler-policy verdict

Knowledge backing `seo-geo` / `scripts/seo/geo_check.py`. It explains *why* the
weighted score is shaped the way it is and *how* a passage earns a citability score,
so a reviewer can judge a run against a fixed rubric instead of vibes. First-principles
and public-standard reasoning only (no third-party method). The math is integer and
time-free, so every score is reproducible.

---

## 1. What "winning" means in AI search

The win condition is **being cited inline by the AI answer**, not ranking #1. That
rewards different properties than classic SEO: a passage has to survive being lifted
out of the page and dropped into a synthesized answer, and the AI crawler has to be
allowed to fetch the page in the first place. The scorecard scores exactly those two
things — *can they reach you* and *is your content quotable once they do* — plus the
machine-readability signals (structured data, llms.txt) that aid extraction.

---

## 2. Passage-level citability (the per-passage 0-100)

A passage is scored on four independent, observable axes. Each is a property you can
verify by eye, which is why the scorer is deterministic.

| Axis | Weight | What it detects | Why it matters for citation |
|---|---|---|---|
| **Sourced** | 0.40 | a number, percentage, year, money figure, or named source | AI engines preferentially quote *specific, verifiable* claims; an unsourced generality is paraphrasable, not quotable |
| **Self-contained** | 0.30 | does **not** open with a back-reference (`this`, `it`, `they`, `however`…) | an extracted passage must read correctly with zero surrounding context |
| **Answer-first** | 0.20 | leads with the claim — not a leading question, not a hedge (`generally`, `it depends`…) | answer engines lift the sentence that *states* the answer, not the one that sets it up |
| **Concise** | 0.10 | one passage ≈ one claim (≤120 words) | a tight, single-claim block is a clean citation unit; a wall of text dilutes it |

`citability_score = round(100 × (0.40·sourced + 0.30·self_contained + 0.20·answer_first + 0.10·concise))`.

**The `citable` boolean is stricter and separate** (it is the long-standing contract
the rest of the pipeline and the smoke test rely on): a passage is `citable` only when
it is **sourced AND self-contained AND ≤120 words**. There is deliberately **no lower
word floor** — a short, sourced, standalone stat ("Northwind Retail holds 23% market
share as of January 2026, per the Beacon Index.") is the densest, most-quotable form and must score
high, not be penalized for brevity. `answer_first` and the 0-100 score are an
*additional* lens on top of that boolean, never a replacement for it.

**Worked contrast:**
- *"Cedar benches last 20 to 25 years outdoors, according to a 2025 test by the
  Outdoor Furniture Council."* → sourced ✓, self-contained ✓, answer-first ✓,
  concise ✓ → **100**, citable.
- *"It is generally considered a good choice for most settings."* → opens with `It`,
  no number, hedged → only concision scores → **10**, not citable.

The weights rank the axes the way citations actually behave (specificity dominates,
context-independence next, framing third, length a tiebreaker); they are a defensible
default, not a tuned constant, and are kept legible on purpose.

---

## 3. The weighted GEO scorecard (the 0-100)

Four categories roll the page's signals into one score. The weights sum to 100 and
live in one place (`SCORECARD_WEIGHTS` in `geo_check.py`).

| Category | Weight | Source signal | Scoring |
|---|---|---|---|
| **passage_citability** | 45 | mean of the per-passage 0-100 scores | the core lever — being quotable is most of GEO |
| **ai_crawler_access** | 25 | retrieval-bot stance from robots | a gate: blocked retrieval ⇒ 0; partial ⇒ 40; open ⇒ 100 |
| **structured_data** | 20 | JSON-LD block count | 0 blocks ⇒ 0; 1 ⇒ 60; ≥2 ⇒ 100 |
| **llms_txt** | 10 | `/llms.txt` presence | present+headings ⇒ 100; present ⇒ 60; absent ⇒ 0; an emerging, lower-confidence signal, so it is weighted lightest |

**Re-normalization (why a content-only run still scores).** A category with no data
is *excluded*, not scored zero, and the total is re-normalized over the **available
weight**. Offline with only `--content`, just `passage_citability` (45) +
`structured_data` (20) are available, so the score is computed over 65 and the report
names the two excluded categories. This keeps an offline run honest — it never invents
a crawler or llms.txt signal it could not observe, and it never deflates the score for
data it simply did not have. Supplying `--robots` (offline) or `--url` (live) adds
those categories back.

**Grades:** ≥85 `strong` · ≥70 `solid` · ≥50 `developing` · <50 `weak`.

---

## 4. The AI-crawler-policy verdict

The verdict separates the two AI postures a robots.txt expresses and judges them
against the GEO best practice — **stay retrievable even if you opt out of training**.

The crawler registry and evaluator live in `scripts/seo/ai_crawlers.py` (one source
of truth shared with `tech_audit.py`). Four classes, each judged over its *core* tokens
(non-core tokens are reported but never swing a stance):

- **Search engines** (the index AI Overviews / AI Mode / Copilot draw from):
  `Googlebot`, `Bingbot`.
- **Retrieval / AI-search bots** (make you citable): `OAI-SearchBot`,
  `Claude-SearchBot`, `PerplexityBot`.
- **User-triggered fetchers** (a person asked an assistant): `ChatGPT-User`,
  `Claude-User`, `Perplexity-User`.
- **Training bots / control tokens** (feed model training): `GPTBot`, `ClaudeBot`,
  `Google-Extended`, `CCBot`.

A bot's stance follows RFC 9309: every group naming the token merges, a specific group
wins over `*`, the longest matching path rule decides (Allow wins a tie), and `*` / `$`
wildcards apply — evaluated at `/`. A bot in no matching group is `unmentioned`
(default-allow). Per class the stance is `open` (none blocked), `blocked` (all
blocked), or `partial`.

| Verdict | Condition | Read |
|---|---|---|
| `search-engine-blocked` | Googlebot or Bingbot is disallowed | **critical** — also removes AI Overviews / AI Mode / Copilot visibility |
| `retrieval-blocked` | every retrieval bot is disallowed | **anti-pattern** — opting out of AI-answer citation |
| `retrieval-partial` | some retrieval bots blocked | uneven citation coverage |
| `citable-training-blocked` | retrieval open, training blocked | **best practice** — citable, opted out of training |
| `citable-training-partial` | retrieval open, training partly blocked | citable; training mixed |
| `fully-open` | all AI crawlers allowed | citable; no training opt-out |

The verdict drives the `ai_crawler_access` category above: `retrieval_stance` open →
100, partial → 40, blocked → 0 — and a blocked search engine forces 0 regardless. Training stance never lowers the access score — blocking
training crawlers is a legitimate choice that does not hurt citability.

---

## 5. Honesty boundary

The scorecard scores **on-page and policy signals only**. It never emits a fabricated
LLM-mention count or AI-answer citation share — those are `needs_tier1` fields a
DataForSEO/AI-visibility MCP supplies. A Tier-2 run is complete on its own: it returns
the citability score, the weak-passage fix list, the crawler verdict, and the weighted
score, and it names what a higher tier would add.
