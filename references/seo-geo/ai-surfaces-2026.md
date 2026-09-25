# seo-geo — AI Answer Surfaces Playbook (September 2026)

How each AI answer surface finds, chooses and cites sources, and which on-page lever
moves each one. Knowledge, not steps. Dated facts shared with the rest of the family
live in `references/shared/search-landscape-2026.md`; the scoring rubric lives in
`references/geo-scorecard.md`.

## The model every surface shares

1. **Retrieve.** The engine pulls candidate pages from an index (Google's, Bing's, or
   its own AI-search crawler's) or fetches them live for a user.
2. **Decompose.** The engine splits one question into many sub-questions (*query
   fan-out*). AI Mode does this aggressively. A page competes per sub-question, not per
   head query.
3. **Extract.** The engine lifts passages that answer a sub-question on their own, then
   synthesizes and cites them.

So three things decide citation, in this order:
- **Access:** can the right crawler reach the page? This is the robots verdict.
- **Coverage:** does some passage answer each sub-question? This is fan-out coverage.
- **Extractability:** is that passage specific, sourced and self-contained? This is
  passage citability.

## Surface by surface

| Surface | Index / fetcher | What it rewards | Lever in this plugin |
|---|---|---|---|
| Google AI Overviews | Googlebot index; snippet controls apply | Concise, sourced passages; pages already strong in organic | `tech_audit.py` indexability + `nosnippet` check; passage citability |
| Google AI Mode | Googlebot index + heavy query fan-out | Covering the whole task: comparisons, costs, steps, edge cases | `geo_check.py --questions` fan-out coverage |
| ChatGPT search | OAI-SearchBot index + ChatGPT-User live fetch; Bing grounding | Fresh, clearly attributed facts; allow both OpenAI tokens | `ai_crawlers.py` verdict (search + user classes) |
| Perplexity | PerplexityBot index + Perplexity-User live fetch | Citation-dense, recent pages; numbers with sources | citability rubric (sourced + specific) |
| Claude | Claude-SearchBot index + Claude-User live fetch | Self-contained, unambiguous passages; entity clarity | citability + `schema_gen.py --graph` |
| Bing Copilot | Bingbot index; IndexNow speeds freshness | Classic Bing relevance + clear answers | IndexNow guidance; `tech_audit.py` |

Two traps to check every time:
- **Blocking Google-Extended does not remove a site from AI Overviews or AI Mode.**
  Only Googlebot access and snippet controls do.
- **A client-rendered page is invisible to most AI fetchers.** They don't run
  JavaScript. `tech_audit.py` flags shell pages.

## Query fan-out coverage (how `--questions` works)

Give `geo_check.py` the sub-questions a page should answer, one per line. Draft them
from the People-Also-Ask set, `seo-cluster` output, sales and support FAQs, and the
comparisons and costs a buyer checks. For each question the checker finds the passage
sharing the most content terms and counts it **covered** when at least 60% of the
question's key terms appear in that one passage. An uncovered question lists its
missing terms, which is the brief for the passage to write.

This is a **lexical proxy**. It proves a passage *talks about* the sub-question, not
that the answer is right or complete. A covered row still gets a human read, and its
`passage_citable` flag says whether the answering passage would survive extraction.

## llms.txt: what to ship, and how much to expect

Ship a short, curated index: an H1 name, a one-line `>` summary, and H2 sections of
`- [Title](https://absolute-url): note` links, with an `## Optional` section for
material an agent can skip. `llms_txt.py --generate` / `--from-urls` builds one, and
`--validate` checks it. No major engine has confirmed using it, so it carries the
lightest scorecard weight (10). Spend the effort on access, coverage and
extractability first.

## Measuring AI visibility honestly

- **Field truth needs data you may not have.** AI-answer mentions, citation share,
  and AI referral sessions come from a mention-tracking connector (Tier 1) or from
  analytics referrers (chatgpt.com, perplexity.ai, copilot, gemini). Without them,
  report the on-page GEO score plus `needs_tier1`. Never an estimated citation count.
- **Search Console folds AI Overview / AI Mode into web search.** A clicks drop with
  flat or rising impressions is the typical AI-answer signature. Treat it as a
  hypothesis, not proof.
- **Guard the access layer in CI.** `seo-drift` rule D15 (`--robots`) turns a deploy
  that blocks AI-search crawlers or a search engine into a critical alert.
