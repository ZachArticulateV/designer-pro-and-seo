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
"""
import argparse
import json
import re
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

UA = "Mozilla/5.0 (compatible; designer-pro-seo-geo/1.0)"
TRAINING_BOTS = ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot"]
RETRIEVAL_BOTS = ["OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"]
DEPENDENT_START = re.compile(r"^\s*(this|that|these|those|it|they|he|she|here|"
                             r"however|therefore|thus|also|additionally|furthermore)\b", re.I)
SPECIFIC = re.compile(r"(\d{4}|\d+%|\$\d|\d+\.\d+|\b\d{2,}\b|\bper cent\b|\bpercent\b)")


def fetch(url, timeout=8):
    try:
        with urlopen(Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
            return r.read(500_000).decode("utf-8", "replace"), None
    except (URLError, HTTPError, ValueError, TimeoutError) as e:
        return None, str(e)


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


def score_passages(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 40]
    results, citable = [], 0
    for p in paras:
        words = len(p.split())
        sentences = max(1, len(re.findall(r"[.!?]+", p)))
        has_specific = bool(SPECIFIC.search(p))
        standalone = not bool(DEPENDENT_START.match(p))
        # citable: specific claim + readable in isolation + substantive length
        is_citable = has_specific and standalone and 15 <= words <= 120
        if is_citable:
            citable += 1
        reasons = []
        if not has_specific:
            reasons.append("no specific/verifiable signal (add a number, date, or named source)")
        if not standalone:
            reasons.append("opens with a back-reference (won't stand alone if extracted)")
        if words > 120:
            reasons.append("long passage (split so each makes one clear claim)")
        results.append({"preview": p[:80], "words": words, "sentences": sentences,
                        "citable": is_citable, "issues": reasons})
    pct = round(100 * citable / len(paras)) if paras else 0
    return {"passages": len(paras), "citable": citable, "citable_pct": pct,
            "weak": [r for r in results if not r["citable"]][:10]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", help="text/markdown/html file to score")
    ap.add_argument("--url", help="site URL (checks /llms.txt + robots AI policy)")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args()

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
            robots, _ = fetch(f"{p.scheme}://{p.netloc}/robots.txt")
            if robots:
                blocks_t = [b for b in TRAINING_BOTS if re.search(rf"User-agent:\s*{re.escape(b)}", robots, re.I)]
                allows_r = [b for b in RETRIEVAL_BOTS if re.search(rf"User-agent:\s*{re.escape(b)}", robots, re.I)]
                report["ai_crawler_policy"] = {"training_bots_referenced": blocks_t,
                                               "retrieval_bots_referenced": allows_r,
                                               "note": "Best practice: allow retrieval bots (so you're citable) even if you block training crawlers."}
        else:
            report["errors"].append("url must be http(s)")

    if args.human:
        c = report["citability"]
        if c:
            print(f"Passage citability: {c['citable']}/{c['passages']} passages citable ({c['citable_pct']}%)")
            for w in c["weak"]:
                print(f"  - \"{w['preview']}...\" — {'; '.join(w['issues'])}")
        if report["structured_data_blocks"] is not None:
            print(f"Structured data blocks: {report['structured_data_blocks']}")
        if report["llms_txt"] is not None:
            print(f"llms.txt: {report['llms_txt']}")
        if report["ai_crawler_policy"] is not None:
            print(f"AI crawler policy: {report['ai_crawler_policy']}")
        for g in report["guidance"]:
            print(f"  * {g}")
        for e in report["errors"]:
            print(f"[ERROR] {e}")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
