#!/usr/bin/env python3
"""
geo_check.py — Generative Engine Optimization (GEO) checks.

Scores content for AI-citability and checks AI-discovery signals. Based on current
GEO findings: LLMs preferentially cite passages that (a) make specific, verifiable,
sourced claims (numbers, dates, named entities — "information density / specificity
signals", cf. Google patent WO2024064249A1) and (b) stand alone when read out of
context. Structured markup and an llms.txt file further aid AI discovery.

Deterministic (no time-based judgments). Standard library only; degrades offline.

Usage:
  python3 geo_check.py --content article.md            # score passage citability
  python3 geo_check.py --content page.html --url https://site.com   # + llms.txt/robots
  python3 geo_check.py --content page.html --robots robots.txt --scorecard --no-network
                                                       # weighted 0-100 GEO scorecard, offline

Three additive analyses (all deterministic, all run offline):
  * a weighted 0-100 GEO scorecard (`--scorecard`) with a per-category breakdown,
    re-normalized over whichever signals are available so a content-only run still scores;
  * a crawler-policy verdict (`--robots FILE`, or any fetched robots.txt) that parses the
    AI-crawler rules and judges the AI-retrieval vs AI-training stance; and
  * passage-level citability scoring (sourced + self-contained + answer-first → 0-100).
See references/geo-scorecard.md for the weight rationale and the passage rubric.
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError

# --- shared SSRF guard (local sibling in scripts/workflow) -------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import (  # noqa: E402
    safe_open, validate_url, UrlValidationError, SafeFetchError,
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_crawlers  # noqa: E402  (shared AI-crawler registry + robots evaluator)

UA = "Mozilla/5.0 (compatible; designer-pro-seo-geo/1.0)"
TRAINING_BOTS = ai_crawlers.TRAINING_BOTS      # back-compat re-exports
RETRIEVAL_BOTS = ai_crawlers.RETRIEVAL_BOTS
DEPENDENT_START = re.compile(r"^\s*(this|that|these|those|it|they|he|she|here|"
                             r"however|therefore|thus|also|additionally|furthermore)\b", re.I)
SPECIFIC = re.compile(r"(\d{4}|\d+%|\$\d|\d+\.\d+|\b\d{2,}\b|\bper cent\b|\bpercent\b)")
# A passage that opens by hedging is not "answer-first" even if it stands alone.
HEDGE_START = re.compile(r"^\s*(maybe|perhaps|possibly|probably|arguably|generally|"
                         r"in general|usually|typically|sometimes|some say|many believe|"
                         r"it depends|we think|i think|in our opinion)\b", re.I)
LEADING_QUESTION = re.compile(r"^[^.!?]*\?")

# --- AI-crawler-policy weighting (see references/geo-scorecard.md) -------------
# Weights sum to 100; the scorecard re-normalizes over whichever categories have data.
SCORECARD_WEIGHTS = {
    "passage_citability": 45,   # the core GEO lever: being quotable in isolation
    "structured_data": 20,      # machine-readable claims aid extraction/attribution
    "ai_crawler_access": 25,    # if retrieval bots can't reach you, nothing else matters
    "llms_txt": 10,             # emerging, lower-confidence discoverability signal
}

# Smart-punctuation / dash / arrow -> ASCII map for the --human render (the contract
# promises ASCII human output). Anything left over is hard-replaced.
_ASCII_MAP = {
    "—": "--", "–": "-", "→": "->", "←": "<-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "•": "*", " ": " ", "·": "-",
}


class _JsonArgParser(argparse.ArgumentParser):
    """argparse's own failures (a missing required arg, a bad type/choice) must honor the
    JSON-error contract too: emit {"error": ...} to stdout + a non-zero exit, never a bare
    usage dump to stderr. stdlib + ASCII."""
    def error(self, message):
        msg = str(message).encode("ascii", "replace").decode("ascii")
        print(json.dumps({"error": msg}))
        sys.exit(2)


def _ascii(s):
    """ASCII-sanitize a human line: map common smart punctuation / em-dashes / arrows to
    ASCII, then hard-replace any residual non-ASCII so --human output is pure ASCII."""
    s = str(s)
    for k, v in _ASCII_MAP.items():
        s = s.replace(k, v)
    return s.encode("ascii", "replace").decode("ascii")


def fetch(url, timeout=8):
    """SSRF-guarded GET via the shared net_safety.safe_open (validates the URL and every
    redirect hop before fetching). Never raises; returns (text, None) or (None, error)."""
    try:
        resp, _chain = safe_open(url, timeout=timeout, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError) as e:
        return None, str(e)
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, str(e)
    try:
        status = getattr(resp, "status", None) or getattr(resp, "code", None)
        if status is not None and status >= 400:
            return None, "HTTP %s" % status
        return resp.read(500_000).decode("utf-8", "replace"), None
    except (URLError, HTTPError, ValueError, TimeoutError, OSError) as e:
        return None, str(e)
    finally:
        try:
            resp.close()
        except Exception:
            pass


def strip_html(text):
    if "<" not in text:
        return text, 0
    ld = len(re.findall(r'application/ld\+json', text, re.I))
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    # paragraphs from block tags
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|section|article)>", "\n\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    return text, ld


def passage_citability(p):
    """Score one passage for AI-citation readiness on three independent axes — sourced
    (a number/date/named signal), self-contained (stands alone when extracted), and
    answer-first (leads with the claim, not a question or a hedge) — plus a concision
    component. Returns a 0-100 `citability_score` AND the unchanged `citable` boolean
    (sourced AND self-contained AND <=120 words) the rest of the pipeline relies on.

    Weights: sourced .40, self-contained .30, answer-first .20, concise .10. They are a
    first-principles ranking of what makes a passage quotable, documented in
    references/geo-scorecard.md; the math is integer and time-free, so it is deterministic.
    """
    p = p.strip()
    words = len(p.split())
    sentences = max(1, len(re.findall(r"[.!?]+", p)))
    sourced = bool(SPECIFIC.search(p))
    self_contained = not bool(DEPENDENT_START.match(p))
    answer_first = (self_contained
                    and not bool(LEADING_QUESTION.match(p))
                    and not bool(HEDGE_START.match(p)))
    concise = 0 < words <= 120
    # is_citable preserves the original contract exactly (no word floor).
    is_citable = sourced and self_contained and words <= 120
    score = round(100 * (0.40 * sourced + 0.30 * self_contained
                         + 0.20 * answer_first + 0.10 * concise))
    reasons = []
    if not sourced:
        reasons.append("no specific/verifiable signal (add a number, date, or named source)")
    if not self_contained:
        reasons.append("opens with a back-reference (won't stand alone if extracted)")
    if not answer_first and self_contained:
        reasons.append("buries the answer (lead with the claim, not a question or hedge)")
    if words > 120:
        reasons.append("long passage (split so each makes one clear claim)")
    return {"preview": p[:80], "words": words, "sentences": sentences,
            "sourced": sourced, "self_contained": self_contained,
            "answer_first": answer_first, "citability_score": score,
            "citable": is_citable, "issues": reasons}


def score_passages(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 40]
    results = [passage_citability(p) for p in paras]
    citable = sum(1 for r in results if r["citable"])
    pct = round(100 * citable / len(paras)) if paras else 0
    mean = round(sum(r["citability_score"] for r in results) / len(paras)) if paras else 0
    return {"passages": len(paras), "citable": citable, "citable_pct": pct,
            "citability_mean": mean,
            "weak": [r for r in results if not r["citable"]][:10]}


# --- AI-crawler policy -------------------------------------------------------
# The crawler registry + RFC 9309 evaluator live in ai_crawlers.py (one source of truth
# shared with tech_audit); this wrapper keeps the report shape geo_check has always had.

def analyze_robots(text):
    """Judge a site's AI-crawler policy: are AI *search* bots (the ones that make you
    citable) allowed, is a classic search engine blocked (that also kills AI Overviews /
    AI Mode visibility), and what is the AI *training* stance? Best practice is to allow
    search + user-triggered fetchers even when training is blocked. Deterministic."""
    v = ai_crawlers.verdict(text)
    cls = v["classes"]

    def split(name):
        return {"allowed": cls[name]["allowed"], "blocked": cls[name]["blocked"]}

    return {
        "verdict": v["verdict"],
        "search_engine_stance": cls["search_engine"]["stance"],
        "retrieval_stance": cls["search"]["stance"],
        "user_fetch_stance": cls["user"]["stance"],
        "training_stance": cls["training"]["stance"],
        "search_engine_bots": split("search_engine"),
        "retrieval_bots": split("search"),
        "user_fetch_bots": split("user"),
        "training_bots": split("training"),
        # backward-compatible keys (a bot is "referenced" if a group names it)
        "retrieval_bots_referenced": cls["search"]["explicitly_named"],
        "training_bots_referenced": cls["training"]["explicitly_named"],
        "sitemaps": v["sitemaps"],
        "note": v["note"],
    }


# --- weighted GEO scorecard --------------------------------------------------

def _grade(score):
    if score >= 85:
        return "strong"
    if score >= 70:
        return "solid"
    if score >= 50:
        return "developing"
    return "weak"


def build_scorecard(report):
    """Weight the gathered GEO signals into a 0-100 score with a per-category breakdown.
    Categories with no data (e.g. llms.txt offline) are excluded and the score is
    re-normalized over the available weight, so a content-only run still yields a real
    number (clearly labeled with which categories were excluded). Deterministic."""
    cats = []

    cit = report.get("citability")
    cats.append({"name": "passage_citability", "available": cit is not None,
                 "score": cit["citability_mean"] if cit else None,
                 "note": "mean passage citability" if cit
                         else "no content scored — pass --content"})

    sd = report.get("structured_data_blocks")
    sd_score = None
    if sd is not None:
        sd_score = 100 if sd >= 2 else (60 if sd == 1 else 0)
    cats.append({"name": "structured_data", "available": sd is not None, "score": sd_score,
                 "note": ("%d JSON-LD block(s)" % sd) if sd is not None
                         else "no content scored — pass --content"})

    pol = report.get("ai_crawler_policy")
    has_pol = bool(pol and pol.get("retrieval_stance"))
    cr_score = None
    if has_pol:
        cr_score = {"open": 100, "partial": 40, "blocked": 0}.get(pol["retrieval_stance"], 0)
        if pol.get("search_engine_stance", "open") != "open":
            cr_score = 0     # a blocked Googlebot/Bingbot also removes AI-answer visibility
    cats.append({"name": "ai_crawler_access", "available": has_pol, "score": cr_score,
                 "note": ("retrieval %s" % pol["retrieval_stance"]) if has_pol
                         else "no robots data — pass --robots or --url"})

    llm = report.get("llms_txt")
    llm_score = None
    if llm is not None:
        if llm.get("present"):
            llm_score = 100 if llm.get("has_headings") else 60
        else:
            llm_score = 0
    cats.append({"name": "llms_txt", "available": llm is not None, "score": llm_score,
                 "note": ("present" if (llm or {}).get("present") else "absent") if llm is not None
                         else "not checked — pass --url"})

    avail = [c for c in cats if c["available"]]
    avail_weight = sum(SCORECARD_WEIGHTS[c["name"]] for c in avail)
    for c in cats:
        w = SCORECARD_WEIGHTS[c["name"]]
        c["weight"] = w
        c["contribution"] = (round(w * c["score"] / avail_weight, 1)
                             if c["available"] and avail_weight else 0.0)
    if avail_weight:
        score = round(sum(SCORECARD_WEIGHTS[c["name"]] * c["score"] for c in avail) / avail_weight)
        grade = _grade(score)
    else:
        score, grade = None, None
    return {"score": score, "grade": grade, "available_weight": avail_weight,
            "excluded": [c["name"] for c in cats if not c["available"]],
            "categories": cats}


def main():
    ap = _JsonArgParser()
    ap.add_argument("--content", help="text/markdown/html file to score")
    ap.add_argument("--url", help="site URL (checks /llms.txt + robots AI policy)")
    ap.add_argument("--robots", help="local robots.txt file for an offline crawler-policy verdict")
    ap.add_argument("--scorecard", action="store_true",
                    help="emit a weighted 0-100 GEO score with a per-category breakdown")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args()
    fatal = False

    report = {"citability": None, "structured_data_blocks": None,
              "llms_txt": None, "ai_crawler_policy": None, "errors": [],
              "guidance": ["Make each key passage state one specific, sourced claim "
                           "that stands alone when quoted.",
                           "Add Article/Organization/Breadcrumb schema (top GEO citation factor).",
                           "Keep content current — AI engines weight recency."]}

    if args.content:
        try:
            raw = open(args.content, encoding="utf-8", errors="replace").read()
        except OSError as e:
            report["errors"].append(f"could not read content: {e}")
            raw = ""
        if raw:
            text, ld = strip_html(raw)
            report["structured_data_blocks"] = ld
            report["citability"] = score_passages(text)

    # A supplied robots.txt (offline) takes precedence and gives the AI-crawler verdict.
    if args.robots:
        try:
            rtext = open(args.robots, encoding="utf-8", errors="replace").read()
            report["ai_crawler_policy"] = analyze_robots(rtext)
        except OSError as e:
            report["errors"].append(f"could not read robots file: {e}")
            fatal = True

    if args.url and not args.no_network:
        if urlparse(args.url).scheme in ("http", "https"):
            p = urlparse(args.url)
            llms, err = fetch(f"{p.scheme}://{p.netloc}/llms.txt")
            if llms:
                report["llms_txt"] = {"present": True,
                                      "has_headings": bool(re.search(r"^#", llms, re.M)),
                                      "bytes": len(llms)}
            else:
                report["llms_txt"] = {"present": False, "note": "Add /llms.txt (Markdown) summarizing the site for LLMs."}
            if not args.robots:   # don't override an explicitly supplied robots file
                robots, _ = fetch(f"{p.scheme}://{p.netloc}/robots.txt")
                if robots:
                    report["ai_crawler_policy"] = analyze_robots(robots)
        else:
            report["errors"].append("url must be http(s)")

    if args.scorecard:
        report["geo_score"] = build_scorecard(report)

    if args.human:
        def emit(line):
            print(_ascii(line))   # ASCII-sanitize the ENTIRE human render path
        gs = report.get("geo_score")
        if gs and gs["score"] is not None:
            emit(f"GEO score: {gs['score']}/100 ({gs['grade']}) "
                 f"[weighted over {gs['available_weight']}/100 available]")
            for cat in gs["categories"]:
                mark = f"{cat['score']}" if cat["available"] else "n/a"
                emit(f"  - {cat['name']}: {mark} ({cat['note']})")
        c = report["citability"]
        if c:
            emit(f"Passage citability: {c['citable']}/{c['passages']} passages citable "
                 f"({c['citable_pct']}%); mean readiness {c['citability_mean']}/100")
            for w in c["weak"]:
                emit(f"  - \"{w['preview']}...\" -- {'; '.join(w['issues'])}")
        if report["structured_data_blocks"] is not None:
            emit(f"Structured data blocks: {report['structured_data_blocks']}")
        if report["llms_txt"] is not None:
            emit(f"llms.txt: {report['llms_txt']}")
        if report["ai_crawler_policy"] is not None:
            pol = report["ai_crawler_policy"]
            emit(f"AI crawler policy: {pol.get('verdict', '?')} -- {pol.get('note', '')}")
        for g in report["guidance"]:
            emit(f"  * {g}")
        for e in report["errors"]:
            emit(f"[ERROR] {e}")
    else:
        print(json.dumps(report, indent=2))

    if fatal:
        sys.exit(2)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
