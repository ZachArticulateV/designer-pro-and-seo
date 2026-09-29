#!/usr/bin/env python3
"""
content_audit.py — deterministic content-quality audit for one page (HTML, Markdown or
plain text): the observable half of E-E-A-T, structure, readability, depth, on-page
keyword use, links, originality / scaled-content risk, and passage citability.

Eight dimensions, each finding a {dimension, severity, finding, fix} record:

  eeat         byline, author profile / credentials, publish + updated dates, staleness
               (with --as-of), sourcing of statistics, first-hand experience markers,
               about/contact trust links — a stricter bar on YMYL topics
  structure    one H1, heading-level skips, H2 sections on long content
  readability  mean sentence length, very long sentences, wall-of-text paragraphs,
               Flesch reading ease (reported)
  depth        word count against the page type's floor; lists/tables on long pages
  keyword      (with --keyword) title / H1 / intro / subheading / meta / slug placement,
               stuffing
  links        internal + external counts, generic anchor text
  originality  template-placeholder leaks, boilerplate filler phrasing, duplicated
               sentences — the scaled-content-abuse tells
  citability   passage citability from geo_check (sourced + specific + standalone)

What it will NOT do: call anything "AI-written", or emit a single number presented as
Google's E-E-A-T score. It reports observable signals, labeled as such, plus a
deterministic 0-100 content score (100 − 25/critical − 10/high − 4/medium).

Usage:
  python3 content_audit.py --file page.html [--url https://site/page] [--keyword "cedar bench"]
                           [--type article|product|local|home|category] [--ymyl auto|yes|no]
                           [--as-of 2026-09-25] [--human]
  python3 content_audit.py --url https://site/page     # SSRF-guarded fetch

Standard library only. Deterministic for a given input and --as-of.
"""
import argparse
import datetime as _dt
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import safe_open, UrlValidationError, SafeFetchError  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo_check  # noqa: E402  (passage citability — one scorer for the family)

UA = "Mozilla/5.0 (compatible; designer-pro-seo-content/1.0)"
SEVERITIES = ("critical", "high", "medium", "info")
PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}
DIMENSIONS = ("eeat", "structure", "readability", "depth", "keyword", "links",
              "originality", "citability")
# word-count floor per page type: (high-below, medium-below)
DEPTH_FLOOR = {"article": (300, 600), "product": (80, 150), "local": (150, 250),
               "home": (150, 250), "category": (80, 150)}

YMYL_TERMS = re.compile(
    r"\b(health|medical|medicine|medication|dosage|diagnos\w*|symptom\w*|treatment|therapy|"
    r"therapist|disease|cancer|diabetes|pregnan\w*|mental health|addiction|rehab\w*|"
    r"detox|overdose|suicid\w*|depression|anxiety|trauma|ptsd|surgery|clinic\w*|"
    r"loan|mortgage|credit score|debt|invest\w*|retirement|tax(es)?|insurance|"
    r"bankruptcy|lawyer|attorney|legal advice|lawsuit|custody|immigration|visa)\b", re.I)
CREDENTIALS = re.compile(
    r"\b(M\.?D\.?|D\.?O\.?|Ph\.?D\.?|Psy\.?D\.?|R\.?N\.?|N\.?P\.?|LCSW|LMFT|LPC|LCADC|CADC|"
    r"CPA|CFP|J\.?D\.?|Esq\.?|PharmD|board[- ]certified|licensed|medically reviewed|"
    r"clinically reviewed|reviewed by|fact[- ]checked)\b")
FIRST_HAND = re.compile(
    r"\b(we tested|we tried|we measured|we compared|we visited|i tested|i tried|i used|"
    r"in our (experience|testing|clinic|practice)|hands-on|our team (tested|found|built)|"
    r"we found that|after \d+ (days|weeks|months|years) of|our (own )?data|we surveyed|"
    r"case study|in my (experience|practice))\b", re.I)
STAT = re.compile(r"(\d+(\.\d+)?\s?%|\$\s?\d[\d,]*(\.\d+)?|\b\d{1,3}(,\d{3})+\b|"
                  r"\b\d+(\.\d+)?\s?(million|billion|thousand)\b)", re.I)
FILLER = [
    "in today's fast-paced world", "in today's digital age", "ever-evolving landscape",
    "it's important to note", "it is important to note", "it's worth noting",
    "delve into", "delves into", "unlock the power", "unlock the potential",
    "game-changer", "game changer", "look no further", "navigate the complexities",
    "a testament to", "in the realm of", "whether you're a", "take it to the next level",
    "at the end of the day", "in conclusion,", "seamlessly integrate", "harness the power",
    "elevate your", "embark on a journey", "the world of", "rest assured",
    "a comprehensive guide", "plays a crucial role", "plays a vital role", "tapestry",
]
PLACEHOLDERS = re.compile(
    r"(lorem ipsum|\{\{\s*[\w.]+\s*\}\}|\[(city|state|keyword|business name|location|"
    r"insert[^\]]*)\]|\bTODO\b|\bTBD\b|XXX+|%%\w+%%|\bINSERT (KEYWORD|CITY|NAME)\b)", re.I)
GENERIC_ANCHORS = {"click here", "here", "read more", "learn more", "more", "this",
                   "this page", "link", "go", "continue", "details", "more info"}


# --- document model -------------------------------------------------------------------

class _Doc(HTMLParser):
    _SKIP = {"script", "style", "noscript", "template", "svg", "nav", "footer", "header",
             "aside", "form"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.headings, self.paras = "", {}, [], []
        self.links, self.times, self.ld, self.lists, self.tables = [], [], [], 0, 0
        self.all_links = []
        self._stack, self._buf, self._in, self._link, self._ld = [], [], None, None, None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in self._SKIP:
            self._skip += 1
        if tag == "script" and "ld+json" in a.get("type", "").lower():
            self._ld = []
        if tag == "meta":
            k = (a.get("name") or a.get("property") or "").lower()
            if k:
                self.meta.setdefault(k, a.get("content", ""))
        elif tag == "time":
            self.times.append(a.get("datetime", ""))
        elif tag == "a":
            self._link = {"href": a.get("href", ""), "rel": a.get("rel", "").lower(),
                          "text": [], "chrome": self._skip > 0}
        elif tag in ("ul", "ol") and not self._skip:
            self.lists += 1
        elif tag == "table" and not self._skip:
            self.tables += 1
        elif tag == "link" and "author" in a.get("rel", "").lower():
            self.meta.setdefault("rel-author", a.get("href", ""))
        if tag in ("title", "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "blockquote"):
            self._in, self._buf = tag, []

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.ld.append("".join(self._ld))
            self._ld = None
        if tag == "a" and self._link is not None:
            self._link["text"] = " ".join("".join(self._link["text"]).split())
            self.all_links.append(self._link)
            if not self._link["chrome"]:
                self.links.append(self._link)
            self._link = None
        if tag == self._in:
            text = " ".join("".join(self._buf).split())
            if tag == "title":
                self.title = text
            elif tag[0] == "h" and len(tag) == 2 and not self._skip:
                self.headings.append((int(tag[1]), text))
            elif text and not self._skip:
                self.paras.append(text)
            self._in = None
        if tag in self._SKIP:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
            return
        if self._link is not None:
            self._link["text"].append(data)
        if self._in:
            self._buf.append(data)


def parse(raw):
    """HTML, Markdown or plain text -> a _Doc-shaped object."""
    is_html = re.search(r"<(!doctype|html|body)\b", raw, re.I) or (
        re.search(r"<(p|h1|div|article)\b", raw, re.I) and not re.search(r"^#{1,6}\s", raw, re.M))
    if is_html:
        d = _Doc()
        d.feed(raw)
        d.close()
        d.kind = "html"
        return d
    d = _Doc()
    d.kind = "markdown" if re.search(r"^#{1,6}\s|\]\(", raw, re.M) else "text"
    for block in re.split(r"\n\s*\n", raw):
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", block.splitlines()[0])
        if m:
            d.headings.append((len(m.group(1)), m.group(2).strip()))
            if len(m.group(1)) == 1 and not d.title:
                d.title = m.group(2).strip()
            rest = "\n".join(block.splitlines()[1:]).strip()
            if not rest:
                continue
            block = rest
        if re.match(r"^\s*([-*]|\d+\.)\s", block):
            d.lists += 1
        if re.match(r"^\s*\|.*\|", block):
            d.tables += 1
        for t, u in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", block):
            d.links.append({"href": u, "rel": "", "text": t, "chrome": False})
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", block)
        text = re.sub(r"[*_`>#|]", " ", text)
        d.paras.append(" ".join(text.split()))
    d.all_links = list(d.links)
    return d


# --- text metrics -----------------------------------------------------------------------

def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text) if len(s.split()) >= 3]


def _syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")):
        n -= 1
    return max(1, n)


def flesch(text):
    words = re.findall(r"[A-Za-z']+", text)
    sents = max(1, len(_sentences(text)))
    if not words:
        return None
    syl = sum(_syllables(w) for w in words)
    return round(206.835 - 1.015 * (len(words) / sents) - 84.6 * (syl / len(words)), 1)


def _ld_facts(blocks):
    facts = {"author": None, "datePublished": None, "dateModified": None}

    def walk(n):
        if isinstance(n, dict):
            for k in ("datePublished", "dateModified"):
                if isinstance(n.get(k), str) and not facts[k]:
                    facts[k] = n[k]
            a = n.get("author")
            if a and not facts["author"]:
                a = a[0] if isinstance(a, list) and a else a
                facts["author"] = a.get("name") if isinstance(a, dict) else (a if isinstance(a, str) else None)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    for b in blocks:
        try:
            walk(json.loads(b))
        except ValueError:
            pass
    return facts


def _parse_date(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if not m:
        return None
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# --- the audit ----------------------------------------------------------------------------

def audit(raw, url=None, keyword=None, page_type="article", ymyl="auto", as_of=None):
    d = parse(raw)
    checks = []

    def add(sev, dim, finding, fix=""):
        checks.append({"dimension": dim, "severity": sev, "finding": finding, "fix": fix})

    body = " ".join(d.paras)
    words = len(body.split())
    host = urlparse(url).netloc.lower() if url else ""
    is_ymyl = (ymyl == "yes") or (ymyl == "auto" and len(YMYL_TERMS.findall(
        " ".join([d.title, body]))) >= 3)
    facts = _ld_facts(d.ld)

    # ---- eeat --------------------------------------------------------------------------
    byline = (d.meta.get("author") or facts["author"] or d.meta.get("article:author")
              or d.meta.get("rel-author"))
    if not byline:
        m = re.search(r"\b(?:By|Written by|Author:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z.]+){1,3})", raw)
        byline = m.group(1) if m else None
    if page_type == "article":
        if byline:
            add("info", "eeat", f"byline: {byline}")
        else:
            add("high", "eeat", "No identifiable author (meta author, schema author, or byline)",
                "Name a real author with a linked profile page (Person schema + bio).")
    creds = CREDENTIALS.search(raw)
    if is_ymyl:
        add("info", "eeat", "YMYL topic detected -- evidence bar raised")
        if not creds:
            add("high", "eeat", "YMYL page shows no credentials or expert review",
                "Add the author's or reviewer's credentials (e.g. 'Clinically reviewed by "
                "<name>, LCSW') and link their profile.")
    elif creds:
        add("info", "eeat", f"credential/review marker: {creds.group(0)}")

    published = facts["datePublished"] or d.meta.get("article:published_time") or \
        next((t for t in d.times if t), None)
    modified = facts["dateModified"] or d.meta.get("article:modified_time")
    if page_type == "article":
        if not published:
            add("medium", "eeat", "No machine-readable publish date",
                "Show the publish date and mark it up (datePublished / <time datetime>).")
        if as_of and (modified or published):
            ref = _parse_date(modified or published)
            if ref:
                age = (as_of - ref).days
                if age > 730:
                    add("medium", "eeat", f"Content last dated {age // 30} months ago",
                        "Review and refresh facts; update dateModified only for real edits.")
                elif age > 365 and is_ymyl:
                    add("medium", "eeat", f"YMYL content last dated {age // 30} months ago",
                        "Re-review YMYL facts at least yearly.")
        pd, md = _parse_date(published), _parse_date(modified)
        if pd and md and md < pd:
            add("medium", "eeat", "dateModified is earlier than datePublished",
                "Fix the dates; dateModified must reflect the last real edit.")

    externals = [l for l in d.links if urlparse(l["href"]).netloc
                 and urlparse(l["href"]).netloc.lower() != host]
    stats = len(STAT.findall(body))
    if stats >= 2 and not externals:
        add("medium", "eeat", f"{stats} statistics with no outbound source link",
            "Link each statistic to its primary source (study, dataset, official page).")
    fh = FIRST_HAND.findall(body)
    if page_type == "article":
        if fh:
            add("info", "eeat", f"{len(fh)} first-hand experience marker(s)")
        elif words >= 400:
            add("medium", "eeat", "No first-hand experience markers",
                "Add what you actually did, measured, or saw (tests, photos, cases).")
    link_hrefs = " ".join(l["href"].lower() for l in d.all_links)
    trust = [p for p in ("about", "contact") if f"/{p}" in link_hrefs]
    if d.kind == "html" and not trust:
        add("medium", "eeat", "No About or Contact link on the page",
            "Link About and Contact pages (sitewide footer is enough).")

    # ---- structure ---------------------------------------------------------------------------
    h1 = [t for lvl, t in d.headings if lvl == 1]
    if not h1:
        add("high", "structure", "No H1", "Add one H1 stating the page topic.")
    elif len(h1) > 1:
        add("medium", "structure", f"{len(h1)} H1 headings", "Keep one H1; demote the rest.")
    prev = None
    skips = 0
    for lvl, _t in d.headings:
        if prev and lvl > prev + 1:
            skips += 1
        prev = lvl
    if skips:
        add("medium", "structure", f"{skips} heading-level skip(s) (e.g. H2 -> H4)",
            "Nest headings in order so the outline (and screen readers) make sense.")
    h2 = [t for lvl, t in d.headings if lvl == 2]
    if words > 600 and not h2:
        add("medium", "structure", f"{words} words with no H2 sections",
            "Break the content into descriptive H2 sections (answer-first).")
    if h2:
        q = sum(1 for t in h2 if t.strip().endswith("?"))
        add("info", "structure", f"{len(h2)} H2 section(s), {q} phrased as questions")

    # ---- readability ----------------------------------------------------------------------------
    sents = _sentences(body)
    if sents:
        lens = [len(s.split()) for s in sents]
        mean = sum(lens) / len(lens)
        long_share = sum(1 for n in lens if n > 30) / len(lens)
        if mean > 25:
            add("medium", "readability", f"Mean sentence length {mean:.0f} words",
                "Aim for ~15-20 words on average; split compound sentences.")
        if long_share > 0.25 and len(lens) >= 4:
            add("medium", "readability", f"{round(long_share * 100)}% of sentences exceed 30 words",
                "Split long sentences; one idea per sentence.")
        walls = [p for p in d.paras if len(p.split()) > 150]
        if walls:
            add("medium", "readability", f"{len(walls)} paragraph(s) over 150 words",
                "Break walls of text into 2-4 sentence paragraphs.")
        fr = flesch(body)
        add("info", "readability", f"Flesch reading ease {fr} (mean sentence {mean:.0f} words)")

    # ---- depth -------------------------------------------------------------------------------------
    hi, med = DEPTH_FLOOR.get(page_type, DEPTH_FLOOR["article"])
    if words < hi:
        art = "an" if page_type[0] in "aeiou" else "a"
        add("high", "depth", f"{words} words -- thin for {art} {page_type} page (floor {hi})",
            "Add the substance the intent needs: specifics, examples, comparisons, FAQs.")
    elif words < med:
        art = "an" if page_type[0] in "aeiou" else "a"
        add("medium", "depth", f"{words} words -- light for {art} {page_type} page",
            "Cover the follow-up questions a reader would ask next.")
    else:
        add("info", "depth", f"{words} words")
    if words > 1200 and not (d.lists or d.tables):
        add("info", "depth", "Long page with no lists or tables",
            "Use a list or table where it aids scanning (steps, specs, comparisons).")

    # ---- keyword -----------------------------------------------------------------------------------
    if keyword:
        kw = keyword.lower().strip()
        where = {
            "title": kw in d.title.lower(),
            "h1": any(kw in t.lower() for t in h1),
            "intro": kw in " ".join(body.split()[:100]).lower(),
            "subheading": any(kw in t.lower() for lvl, t in d.headings if lvl >= 2),
            "meta description": kw in d.meta.get("description", "").lower(),
        }
        if url:
            where["url slug"] = all(w in urlparse(url).path.lower() for w in kw.split())
        missing = [k for k, v in where.items() if not v]
        if not where["title"] or not where["h1"]:
            add("high", "keyword", f'"{keyword}" missing from ' +
                " and ".join(k for k in ("title", "h1") if not where[k]),
                "Put the primary topic in the title and H1, naturally phrased.")
        rest = [m for m in missing if m not in ("title", "h1")]
        if rest:
            add("medium" if "intro" in rest else "info", "keyword",
                f'"{keyword}" not in: ' + ", ".join(rest),
                "Mention the topic in the first 100 words and one subheading.")
        occurrences = body.lower().count(kw)
        density = occurrences * len(kw.split()) / max(1, words) * 100
        if density > 3 and occurrences > 5:
            add("medium", "keyword", f'"{keyword}" density {density:.1f}% (stuffing risk)',
                "Use synonyms and natural phrasing; write for the reader.")

    # ---- links --------------------------------------------------------------------------------------
    internals = [l for l in d.links if l["href"] and not l["href"].startswith(("#", "mailto:", "tel:"))
                 and (not urlparse(l["href"]).netloc or urlparse(l["href"]).netloc.lower() == host)]
    if d.kind != "text":
        if not internals and words >= 250:
            add("high", "links", "No in-content internal links",
                "Link to 2-5 related pages (hub, siblings, next step) with descriptive anchors.")
        else:
            add("info", "links", f"{len(internals)} internal / {len(externals)} external in-content link(s)")
        generic = [l for l in d.links if l["text"].lower().strip(" .!>") in GENERIC_ANCHORS]
        if generic:
            add("medium", "links", f"{len(generic)} generic anchor(s) (e.g. \"{generic[0]['text']}\")",
                "Use anchors that describe the destination.")

    # ---- originality ---------------------------------------------------------------------------------
    ph = PLACEHOLDERS.findall(raw if d.kind != "html" else " ".join([d.title, body]))
    if ph:
        first = ph[0][0] if isinstance(ph[0], tuple) else ph[0]
        add("critical", "originality", f"Template placeholder leaked into content: {first!r}",
            "Fill or remove the placeholder; leaked tokens are a scaled-content tell.")
    low = body.lower()
    hits = sorted({f for f in FILLER if f in low})
    rate = len(hits) / max(1, words) * 1000
    if len(hits) >= 6 or (len(hits) >= 3 and rate > 4):
        add("high" if len(hits) >= 6 else "medium", "originality",
            f"{len(hits)} generic filler phrase(s): " + ", ".join(hits[:4]),
            "Replace filler with specifics only you can say (numbers, cases, opinions).")
    elif hits:
        add("info", "originality", "filler phrase(s): " + ", ".join(hits))
    norm = [re.sub(r"\W+", " ", s.lower()).strip() for s in sents if len(s.split()) >= 6]
    dups = len(norm) - len(set(norm))
    if dups:
        add("medium", "originality", f"{dups} duplicated sentence(s)",
            "Remove repeated sentences; repetition reads as templated content.")

    # ---- citability -------------------------------------------------------------------------------------
    cit = geo_check.score_passages("\n\n".join(d.paras))
    if cit["passages"]:
        sev = "medium" if cit["citable_pct"] < 40 and cit["passages"] >= 3 else "info"
        add(sev, "citability",
            f"{cit['citable']}/{cit['passages']} passages citable ({cit['citable_pct']}%)",
            "Rewrite weak passages to lead with one specific, sourced claim."
            if sev == "medium" else "")

    score = max(0, 100 - sum(PENALTY[c["severity"]] for c in checks))
    dims = {dm: {s: sum(1 for c in checks if c["dimension"] == dm and c["severity"] == s)
                 for s in SEVERITIES} for dm in DIMENSIONS}
    return {"kind": d.kind, "page_type": page_type, "ymyl": is_ymyl, "words": words,
            "title": d.title, "headings": len(d.headings), "score": score,
            "score_basis": "100 minus 25/critical, 10/high, 4/medium over observed signals; "
                           "not Google's E-E-A-T and not an AI-detection verdict",
            "dimensions": dims, "checks": checks,
            "citability": {"citable_pct": cit["citable_pct"], "passages": cit["passages"],
                           "weak": [w["preview"] for w in cit["weak"]][:5]}}


def _fetch(url):
    try:
        resp, _ = safe_open(url, timeout=10, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError, OSError, ValueError) as e:
        return None, str(e)
    try:
        return resp.read(4_000_000).decode("utf-8", "replace"), None
    except OSError as e:
        return None, str(e)
    finally:
        resp.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="content-quality audit")
    ap.add_argument("--file", help="HTML / Markdown / text file")
    ap.add_argument("--url", help="page URL (context for --file, or fetched when no --file)")
    ap.add_argument("--keyword", help="primary topic / keyword")
    ap.add_argument("--type", default="article", choices=sorted(DEPTH_FLOOR))
    ap.add_argument("--ymyl", default="auto", choices=("auto", "yes", "no"))
    ap.add_argument("--as-of", help="YYYY-MM-DD reference date for staleness checks")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)

    as_of = None
    if a.as_of:
        as_of = _parse_date(a.as_of)
        if not as_of:
            print(json.dumps({"error": "--as-of must be YYYY-MM-DD"}))
            return 1
    raw, err = None, None
    if a.file:
        try:
            with open(a.file, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError as e:
            err = f"could not read {a.file}: {e}"
    elif a.url and not a.no_network:
        raw, err = _fetch(a.url)
    else:
        err = "provide --file, or --url without --no-network"
    if raw is None or not raw.strip():
        print(json.dumps({"error": err or "empty input"}))
        return 1

    r = audit(raw, a.url, a.keyword, a.type, a.ymyl, as_of)
    if a.human:
        print(f"# Content audit: {a.file or a.url}  ({r['kind']}, {r['page_type']}, "
              f"{r['words']} words{', YMYL' if r['ymyl'] else ''})  score {r['score']}/100")
        for s in SEVERITIES:
            for c in r["checks"]:
                if c["severity"] == s:
                    print(f"[{s.upper()}] ({c['dimension']}) {c['finding']}")
                    if c["fix"] and s != "info":
                        print(f"    fix: {c['fix']}")
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
