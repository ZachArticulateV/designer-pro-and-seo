# Search Landscape — Current Facts (as of September 2026)

The single dated reference for "what is true in search right now." Every SEO skill
cites this file instead of hard-coding a fact in its own body, so one edit keeps the
whole family current. Knowledge, not steps. **Review this file every quarter** and
update the "as of" date. When a fact here conflicts with a skill body, this file wins
and the skill is wrong.

## 1. How results are assembled now

- **AI answers sit above the links.** Google's AI Overviews appear on a large share of
  informational queries, and AI Mode (a conversational, multi-step results surface) is
  being pushed harder toward the default experience. Bing Copilot, ChatGPT search,
  Perplexity and Claude all answer with inline citations.
- **AI Overviews and AI Mode are built from Google's normal index.** There is no
  separate "AI index" to submit to. A page must be crawlable by Googlebot, indexable,
  and eligible for a snippet to be cited. The same holds for Bing and Copilot.
- **Clicks are scarcer. Citations are the new impression.** Zero-click results keep
  growing, so measure *being cited* (brand mentions, links inside AI answers,
  referral traffic from AI surfaces) alongside rank and CTR.
- **Search Console counts AI features as web search.** AI Overview and AI Mode
  appearances fold into the Performance report's web search type. There is no
  separate AI filter, so a clicks drop with flat impressions is the typical AI-answer
  signature.

## 2. Ranking systems and spam policies that matter

- **Helpfulness is part of core ranking.** The separate helpful-content classifier was
  folded into the core ranking systems. There is no standalone "HCU recovery" anymore.
  Recovery is about page-level quality and site-level trust over core updates.
- **Spam policies to audit against:** *scaled content abuse* (mass pages made mainly
  to rank, whether by AI, templates or people), *site reputation abuse* (third-party
  pages riding a host's authority), and *expired domain abuse* (buying an old domain
  to rank unrelated content). The August 2026 spam update hit sites mass-publishing
  low-value AI content hard. Programmatic pages need real, unique value per URL.
- **E-E-A-T is a rater framework, not a score.** Trust is the center. Experience
  (first-hand evidence) is the easiest to show and the easiest to fake badly. See
  `eeat-criteria.md`.

## 3. Crawling and indexing limits

- **Mobile-first indexing is complete.** Google crawls and indexes with the smartphone
  agent. Content, links, and structured data missing from the mobile render do not
  exist for Google.
- **Googlebot indexes the first 2 MB of an HTML or text file (uncompressed).** Bytes
  past the cutoff are not considered for indexing. PDFs get 64 MB. Most pages are far
  under the limit. The risk is huge inline JSON (hydration state), inline SVG/base64,
  or giant server-rendered lists pushing real content past 2 MB.
- **JavaScript rendering is deferred and budgeted.** Critical content, links, canonical,
  meta robots and structured data belong in the initial HTML. AI-search crawlers and
  most user-triggered fetchers **do not execute JavaScript**. A client-rendered shell
  is invisible to them.
- **IndexNow** instantly notifies Bing, Yandex, Seznam, Naver and other participating
  engines of changed URLs. Google does not participate. Keep an accurate sitemap
  `lastmod` for Google.
- **Sitemap `lastmod` must be honest.** Google uses it only when it matches real
  content changes. `changefreq` and `priority` are ignored.

## 4. AI crawlers and robots.txt

Four crawler classes are judged separately. The registry and the RFC 9309 evaluator
live in `scripts/seo/ai_crawlers.py`, the single source of truth.

| Class | Examples | Block it and… |
|---|---|---|
| Classic search engine | Googlebot, Bingbot | you vanish from search **and** from AI Overviews / AI Mode / Copilot |
| AI search index | OAI-SearchBot, Claude-SearchBot, PerplexityBot | you stop being cited by that answer engine |
| User-triggered fetch | ChatGPT-User, Claude-User, Perplexity-User | assistants can't read your page when a person asks about you |
| Training / control token | GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot | you opt out of model training; citability is unaffected |

- **Default recommendation:** allow the first three classes, decide training explicitly.
- **Google-Extended does not control AI Overviews or AI Mode.** It governs Gemini
  training and grounding use only. The only way out of AI Overviews is `nosnippet` /
  `max-snippet` or blocking Googlebot, and both cost classic visibility too.
- Each token needs its own group. Blocking `ClaudeBot` does not block
  `Claude-SearchBot` or `Claude-User`.

## 5. Structured data status

Structured data still matters: it disambiguates entities for ranking systems and AI
answers even where no rich result is shown. But several rich-result *displays* are
gone. Keep valid markup, and stop promising the visual.

| Feature | Status |
|---|---|
| FAQ rich results | **Ended May 7, 2026** for all sites. `FAQPage` stays valid schema and useful machine context. |
| HowTo rich results | Removed (desktop and mobile). `HowTo` stays valid schema. |
| Sitelinks search box | Removed. `WebSite` + `SearchAction` no longer produce a search box. Keep `WebSite` for the site name. |
| Course Info, Claim Review, Estimated Salary, Learning Video, Special Announcement, Vehicle Listing | Retired in the 2025 simplification. |
| Book Actions | Retired, then **reinstated** (a Search feature still uses it). |
| Practice Problem | Search Console / Rich Results Test support ended Jan 2026. |
| Dataset | Powers Dataset Search only, not regular Search results. |
| Product / merchant listings, Review snippet, Breadcrumb, Article, Video, Event, Recipe, LocalBusiness, Organization, ProfilePage, DiscussionForumPosting, JobPosting | **Active.** Prioritize these. |

Merchant notes: `hasMerchantReturnPolicy` and `shippingDetails` can be declared once
at the `Organization` level instead of on every `Offer`. Variants belong in
`ProductGroup` + `hasVariant` / `variesBy`.

Removing a rich-result feature is a search-appearance change, not a ranking change.
Do not tear out valid markup because its visual went away.

## 6. Page experience

- Core Web Vitals: **LCP < 2.5 s, INP < 200 ms, CLS < 0.1** at p75 field data. See
  `cwv-thresholds.md`. INP is the most-failed metric.
- HTTPS, no intrusive interstitials, mobile-usable layout. Page experience is a
  tie-breaker, not a trump card over relevance.

## 7. Titles, snippets and SERP presentation

- Google rewrites title links it finds unhelpful. Write a unique, descriptive `<title>`
  that front-loads the topic. Display truncates around **~600 px** (roughly 50–60
  characters).
- Meta descriptions are often rewritten from on-page text. They still help CTR when
  they match intent. Aim for about 120–160 characters.
- `max-snippet`, `max-image-preview:large`, and `nosnippet` / `data-nosnippet` control
  what appears in snippets **and** in AI Overviews.

## 8. AI-answer (GEO) signals that hold up

- **Passage-level answerability:** self-contained paragraphs that state one specific,
  sourced claim and survive being quoted alone. See `../geo-scorecard.md`.
- **Entity clarity:** consistent `Organization` / `Person` markup with `sameAs`, a real
  About page, and authors with profiles.
- **Freshness where it matters:** visible updated dates that reflect real edits.
- **Brand mentions across the web** (reviews, forums, press, video) correlate with AI
  citation more than raw link counts do.
- **`llms.txt`** is a community proposal. No major answer engine has confirmed it as a
  ranking or citation input. It is cheap to ship and low-confidence, so it is weighted
  lightest.

## 9. What changed recently (update log for this file)

- **2026-09 (v1.2–v1.10)** — Encoded into engines: 2 MB limit and X-Robots-Tag
  (`tech_audit.py`), retired rich results and merchant/return/shipping types
  (`schema_gen.py`, `product_audit.py`), crawler classes (`ai_crawlers.py`, drift D15),
  llms.txt structure (`llms_txt.py`), AI Mode query fan-out (`geo_check.py --questions`).
- **2026-09** — File created. Consolidated: 2 MB index limit, FAQ rich-result end,
  AI-crawler classes (search / user / training / search-engine), Google-Extended scope,
  August 2026 spam update, AI Mode default push.
