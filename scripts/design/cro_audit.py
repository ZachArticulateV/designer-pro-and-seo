#!/usr/bin/env python3
"""
cro_audit.py — deterministic conversion-rate heuristics for one page.

Reads the HTML (and the conversion rules in data/ux-rules.csv) and reports what a CRO
review checks first, each finding with Impact / Effort, a leverage rank, and — where one
exists — the ux-rules.csv rule it enforces:

  K1  no call to action at all                    K2  no CTA in the first screen
  K3  competing CTAs in the first screen (> 2 distinct labels)
  K4  generic CTA labels ("Submit", "Learn more", "Click here")
  K5  long forms (> 5 visible fields; > 8 = high)  K6  optional-by-nature fields required
  K7  no trust signals (reviews, ratings, guarantees, credentials, client proof)
  K8  trust signals exist but none near a form / CTA
  K9  no contact path, or a phone number that isn't tap-to-call
  K10 headline problems (none, generic "Welcome…", > 12 words)
  K11 no supporting value copy in the first screen
  K12 autoplaying media with sound / without controls
  K13 no sticky or repeated CTA on a long page

"First screen" is approximated deterministically as the content before the first <h2>
(or the first 20% of the body — at least ~1,500 characters — when there is no <h2>). These are hypotheses to test,
ranked by leverage — not a substitute for an A/B test.

Usage:
  python3 cro_audit.py --file landing.html [--goal lead|call|purchase|signup] [--human]
  python3 cro_audit.py --url https://site/landing        # SSRF-guarded fetch

Standard library only. Deterministic.
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
from net_safety import safe_open, UrlValidationError, SafeFetchError  # noqa: E402

UA = "Mozilla/5.0 (compatible; designer-pro-cro/1.0)"
IMPACT = {"high": 3, "med": 2, "low": 1}
EFFORT = {"low": 1, "med": 2, "high": 3}
SEV = {"high": "high", "med": "medium", "low": "info"}
GENERIC = {"submit", "send", "click here", "learn more", "read more", "go", "continue",
           "more", "details", "enter", "ok", "next", "click"}
CTA_CLASS = re.compile(r"\b(btn|button|cta|call-to-action)\b", re.I)
CTA_WORDS = re.compile(r"\b(get|start|book|buy|shop|order|call|schedule|request|join|"
                       r"sign up|try|claim|reserve|download|contact|subscribe|apply|add to cart)\b", re.I)
TRUST = re.compile(r"\b(testimonial|reviews?|rated|stars?|★|trustpilot|guarantee|warranty|"
                   r"money[- ]back|certified|accredited|licensed|award|as seen (in|on)|"
                   r"clients|customers served|years in business|since (19|20)\d\d|"
                   r"case stud(y|ies)|BBB|insured)\b", re.I)
GENERIC_H1 = re.compile(r"^\s*(welcome|home|homepage|hello|untitled|about us)\b", re.I)
PHONE = re.compile(r"(\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
OPTIONAL_FIELDS = re.compile(r"\b(phone|tel|company|job ?title|address|fax|website)\b", re.I)


def _rules():
    path = os.path.join(ROOT, "data", "ux-rules.csv")
    try:
        with open(path, encoding="utf-8") as fh:
            return {r["rule"]: r for r in csv.DictReader(fh)}
    except (OSError, KeyError):
        return {}


RULE_FOR = {"K1": "One primary CTA per view", "K2": "One primary CTA per view",
            "K3": "One primary CTA per view", "K5": "Minimize required form fields",
            "K6": "Minimize required form fields", "K7": "Trust signals near conversion points",
            "K8": "Trust signals near conversion points", "K10": "Page reflects intent in first 3 seconds",
            "K11": "Value proposition visible without scrolling", "K13": "Sticky CTA on long mobile pages"}


def _text(fragment):
    t = re.sub(r"(?is)<(script|style|noscript|template|svg)\b.*?</\1>", " ", fragment)
    return " ".join(re.sub(r"(?s)<[^>]+>", " ", t).split())


def _ctas(fragment):
    out = []
    for tag, attrs, inner in re.findall(r"(?is)<(a|button)\b([^>]*)>(.*?)</\1>", fragment):
        label = _text(inner)
        if not label:
            continue
        if tag.lower() == "button" or CTA_CLASS.search(attrs) or (
                CTA_WORDS.search(label) and len(label.split()) <= 6 and "href" in attrs.lower()):
            out.append(label)
    for attrs in re.findall(r"(?is)<input\b([^>]*type=[\"'](?:submit|button)[\"'][^>]*)>", fragment):
        m = re.search(r"value=[\"']([^\"']+)", attrs)
        out.append(m.group(1) if m else "Submit")
    return out


def audit(html, goal="lead"):
    rules = _rules()
    found = {}

    def add(code, impact, effort, finding, fix, detail=None):
        f = found.setdefault(code, {"code": code, "impact": impact, "effort": effort,
                                    "severity": SEV[impact], "finding": finding, "fix": fix,
                                    "details": [], "rule": None})
        r = rules.get(RULE_FOR.get(code, ""))
        if r:
            f["rule"] = {"rule": r["rule"], "priority": r.get("priority")}
        if detail and detail not in f["details"]:
            f["details"].append(detail)

    body_m = re.search(r"(?is)<body\b[^>]*>(.*)</body>", html)
    body = body_m.group(1) if body_m else html
    main = re.sub(r"(?is)<(nav|header|footer)\b.*?</\1>", " ", body)
    h2 = re.search(r"(?i)<h2\b", main)
    hero = main[:h2.start()] if h2 else main[:max(1500, len(main) // 5)]
    all_ctas = _ctas(main)
    hero_ctas = _ctas(hero)
    text = _text(main)

    if not all_ctas:
        add("K1", "high", "low", "no call to action on the page",
            "Add one clear, specific primary CTA (e.g. 'Book a free consultation').")
    elif not hero_ctas:
        add("K2", "high", "low", "no call to action in the first screen",
            "Put the primary CTA beside the headline/value proposition.")
    distinct = sorted({c.lower() for c in hero_ctas})
    if len(distinct) > 2:
        add("K3", "med", "low", f"{len(distinct)} competing CTAs in the first screen",
            "Keep one primary CTA (plus at most one secondary, styled quieter).", ", ".join(distinct[:5]))
    for c in all_ctas:
        if c.lower().strip(" .!>→") in GENERIC:
            add("K4", "med", "low", "generic CTA label",
                "Say what happens next: 'Get my quote', 'Start free trial', 'Call now'.", c)

    for form in re.findall(r"(?is)<form\b.*?</form>", main):
        fields = [f for f in re.findall(r"(?is)<(input|select|textarea)\b([^>]*)>", form)
                  if not re.search(r"type=[\"'](hidden|submit|button|image|reset)[\"']", f[1], re.I)]
        n = len(fields)
        if n > 8:
            add("K5", "high", "med", f"form with {n} visible fields",
                "Cut to the fields you act on in the first reply (name, email, one qualifier); "
                "collect the rest later.", f"{n} fields")
        elif n > 5:
            add("K5", "med", "med", f"form with {n} visible fields",
                "Trim to 3-5 fields; every extra field costs completions.", f"{n} fields")
        for _tag, attrs in fields:
            if "required" in attrs.lower() and OPTIONAL_FIELDS.search(attrs):
                name = re.search(r"(name|id|placeholder|aria-label)=[\"']([^\"']+)", attrs)
                add("K6", "med", "low", "optional-by-nature field marked required",
                    "Make phone / company / address optional unless the goal needs them.",
                    name.group(2) if name else "field")

    has_schema_rating = re.search(r'"(aggregateRating|Review)"', html)
    trust_hits = TRUST.findall(text)
    if not trust_hits and not has_schema_rating:
        add("K7", "high", "med", "no trust signals on the page",
            "Add proof near the decision: reviews with names, ratings, guarantees, "
            "credentials, client logos, years in business.")
    else:
        near = False
        for m in re.finditer(r"(?is)<form\b.*?</form>|<button\b.*?</button>", main):
            window = _text(main[max(0, m.start() - 1500):m.end() + 1500])
            if TRUST.search(window):
                near = True
                break
        if (re.search(r"(?i)<form\b|<button\b", main)) and not near:
            add("K8", "med", "low", "trust signals are not near the form / CTA",
                "Move a testimonial, rating or guarantee next to the conversion point.")

    tel = re.search(r"(?i)href=[\"']tel:", html)
    if not (tel or re.search(r"(?i)href=[\"']mailto:", html) or re.search(r"(?i)<form\b", html)):
        add("K9", "high" if goal == "call" else "med", "low", "no contact path (form, tap-to-call, email)",
            "Give visitors a way to act: a short form, a tel: link, or both.")
    elif PHONE.search(text) and not tel:
        add("K9", "high" if goal == "call" else "med", "low", "phone number shown but not tap-to-call",
            'Wrap the number in <a href="tel:+1...">.', PHONE.search(text).group(0))

    h1 = re.search(r"(?is)<h1\b[^>]*>(.*?)</h1>", main)
    if not h1:
        add("K10", "high", "low", "no H1 headline",
            "Lead with a headline that states the outcome for the visitor.")
    else:
        h1t = _text(h1.group(1))
        if GENERIC_H1.match(h1t):
            add("K10", "high", "low", f'generic headline "{h1t}"',
                "Replace with the specific outcome you deliver and for whom.")
        elif len(h1t.split()) > 12:
            add("K10", "med", "low", f"headline is {len(h1t.split())} words",
                "Make it readable in ~3 seconds (6-12 words); move detail to the subhead.")
    hero_words = len(_text(re.sub(r"(?is)<(h1|a|button)\b.*?</\1>", " ", hero)).split())
    if hero_words < 8:
        add("K11", "med", "low", "no supporting value copy in the first screen",
            "Add a one-sentence subhead: what it is, who it's for, why it's better.")

    for v in re.findall(r"(?is)<video\b[^>]*>", html):
        if "autoplay" in v.lower() and ("muted" not in v.lower() or "controls" not in v.lower()):
            add("K12", "med", "low", "autoplaying video without muted + controls",
                "Autoplay only muted, with controls (and respect prefers-reduced-motion).")
    words = len(text.split())
    if words > 1200 and len(all_ctas) < 2 and not re.search(r"(?i)position\s*:\s*sticky|sticky", html):
        add("K13", "med", "low", f"long page ({words} words) with a single CTA",
            "Repeat the primary CTA after key sections or add a sticky mobile CTA.")

    findings = sorted(found.values(), key=lambda f: (-IMPACT[f["impact"]] / EFFORT[f["effort"]],
                                                     int(f["code"][1:])))
    for i, f in enumerate(findings, 1):
        f["leverage_rank"] = i
    penalty = {"high": 10, "medium": 4, "info": 0}
    return {"action": "cro-audit", "goal": goal, "ctas": len(all_ctas),
            "first_screen_ctas": sorted(set(hero_ctas)), "findings": findings,
            "score": max(0, 100 - sum(penalty[f["severity"]] for f in findings)),
            "note": "heuristic hypotheses ranked by impact / effort; validate with an A/B test",
            "manual_checks": ["thumb-zone reach of the primary CTA on a 375 px screen "
                              "(Playwright deepens this)", "page speed on a mid-range phone"]}


def _fetch(url):
    try:
        resp, _ = safe_open(url, timeout=10, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError, OSError, ValueError) as e:
        return None, str(e)
    try:
        return resp.read(4_000_000).decode("utf-8", "replace"), None
    finally:
        resp.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="CRO heuristic audit")
    ap.add_argument("--file")
    ap.add_argument("--url")
    ap.add_argument("--goal", default="lead", choices=("lead", "call", "purchase", "signup"))
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)
    if a.file:
        try:
            with open(a.file, encoding="utf-8", errors="replace") as fh:
                html = fh.read()
        except OSError as e:
            print(json.dumps({"error": f"could not read {a.file}: {e}"}))
            return 1
    elif a.url and not a.no_network:
        html, err = _fetch(a.url)
        if html is None:
            print(json.dumps({"error": err}))
            return 1
    else:
        print(json.dumps({"error": "provide --file, or --url without --no-network"}))
        return 1
    r = audit(html, a.goal)
    if a.human:
        print(f"# CRO audit ({r['goal']}): {a.file or a.url}  {r['ctas']} CTA(s)  score {r['score']}/100")
        for f in r["findings"]:
            print(f"{f['leverage_rank']:>2}. [{f['impact'].upper()} impact / {f['effort']} effort] "
                  f"{f['code']} {f['finding']}")
            for d in f["details"][:3]:
                print(f"      - {d}")
            print(f"      fix: {f['fix']}")
            if f["rule"]:
                print(f"      rule: {f['rule']['rule']} ({f['rule']['priority']})")
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
