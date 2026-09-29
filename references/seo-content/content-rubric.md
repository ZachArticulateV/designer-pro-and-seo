# seo-content / seo-page — Content Rubric, Thresholds & Scoring

The durable knowledge behind `scripts/seo/content_audit.py`. Knowledge, not steps. The
E-E-A-T concept framing lives in `references/shared/eeat-criteria.md`. Passage
citability lives in `references/geo-scorecard.md`. Spam-policy context (scaled content
abuse, the August 2026 spam update) is in `references/shared/search-landscape-2026.md` §2.

## What the audit is, and is not

- **It is** a deterministic read of *observable* quality signals: who wrote it, when,
  whether claims are sourced, how it is structured, how dense and readable it is, and
  whether it carries templated-content tells.
- **It is not** Google's E-E-A-T score, which doesn't exist as a number. It is also
  not an "AI-written" detector. Filler phrasing is reported as *generic phrasing*
  because humans write it too. The fix is the same either way: replace it with
  specifics only you could say.

## Page types and depth floors

Word counts are a *floor for coverage*, not a target. More words never fix a missing
answer.

| `--type` | High below | Medium below | Why |
|---|---|---|---|
| article | 300 | 600 | informational intent needs explanation, evidence, follow-ups |
| local | 150 | 250 | service + area + proof + contact, without padding |
| home | 150 | 250 | who, what, for whom, and the next step |
| product | 80 | 150 | specs, differentiators, and use; reviews add the rest |
| category | 80 | 150 | a short, genuinely useful intro above the grid |

The author, publish-date and first-hand checks apply to `article` pages only.
Product, local and home pages earn trust through other signals.

## YMYL detection and the raised bar

`--ymyl auto` (the default) treats a page as YMYL when **three or more** health, money,
legal or safety terms appear in the title and body. Examples: treatment, therapy,
medication, addiction, mortgage, tax, insurance, lawyer, custody. Force the decision
with `--ymyl yes|no`. On YMYL pages:

- No visible credentials or expert review is **high**. Credentials include MD, PhD,
  RN, LCSW, LMFT, LPC, CADC, CPA, CFP, JD, "clinically/medically reviewed by", and
  "fact-checked".
- Content older than **12 months** is flagged. Non-YMYL pages are flagged after
  **24 months**. Staleness is only judged when `--as-of` is given, so results never
  drift with the wall clock.

Treatment centers, clinics, and financial or legal services are almost always YMYL.
Pair every clinical claim with a reviewer and a source.

## Check catalog and severities

| Dimension | Check | Severity |
|---|---|---|
| originality | template placeholder leaked (`[city]`, `{{ var }}`, lorem ipsum, TODO) | **critical** |
| eeat | no author (meta author, schema author, `rel=author`, or "By Name") | high |
| eeat | YMYL page without credentials or expert review | high |
| structure | no H1 | high |
| depth | under the type's high floor | high |
| keyword | primary topic missing from title and/or H1 | high |
| links | no in-content internal links (≥ 250 words) | high |
| originality | 6+ distinct filler phrases | high |
| eeat | no machine-readable publish date · stale · `dateModified` < `datePublished` · 2+ statistics with no outbound source · no first-hand markers (≥ 400 words) · no About/Contact link | medium |
| structure | several H1s · heading-level skip · over 600 words with no H2 | medium |
| readability | mean sentence over 25 words · more than 25% of sentences over 30 words · paragraph over 150 words | medium |
| depth | under the type's medium floor | medium |
| keyword | topic missing from the intro · density over 3% (stuffing) | medium |
| links | generic anchors ("click here", "read more", "learn more", …) | medium |
| originality | 3+ filler phrases at a high rate · duplicated sentences | medium |
| citability | under 40% of passages citable (3+ passages) | medium |

Navigation, header, footer, aside and form content is excluded from word counts and
in-content links. It still counts toward About/Contact trust links, since a sitewide
footer is enough there.

## Scoring

`score = max(0, 100 − 25·critical − 10·high − 4·medium)`, plus per-dimension counts.
Info findings (a byline found, a Flesch value, a link count) never cost points. The
score's job is to rank pages for triage, not to certify quality.

## Worked example

`references/examples/seo-content/sample-article.html` is a short YMYL recovery article
for a fictional treatment center. Run with `--keyword "sleep and recovery"`, it scores
**13/100**:

- **1 critical × 25:** `[city]` leaked from a template.
- **3 high × 10:** no author; no clinical reviewer on a YMYL page; 144 words.
- **8 medium × 4:**
  - no publish date
  - two uncited statistics (70%, 40%)
  - no About/Contact link
  - an H1→H3 heading skip
  - the topic missing from the intro, subheadings and meta description
  - a "Click here" anchor
  - four filler phrases
  - 1 of 4 passages citable

That gives 100 − 25 − 30 − 32 = 13. The first-hand-experience check doesn't fire here,
because it applies only from 400 words. `tests/test_content_audit.py` pins the score.
