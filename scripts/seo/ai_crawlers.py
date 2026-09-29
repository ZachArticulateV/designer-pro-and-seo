#!/usr/bin/env python3
"""
ai_crawlers.py -- the one source of truth for AI-crawler tokens + robots.txt policy.

Every SEO script that reasons about AI crawlers (geo_check, tech_audit, ...) imports
this module instead of carrying its own bot list, so the plugin never gives two
different answers about the same robots.txt.

What it knows (Sept 2026 landscape, from operators' public crawler docs):
  * four crawler CLASSES, because a site's policy is judged per class, not per bot:
      search_engine -- classic search crawlers (Googlebot, Bingbot). Google's AI
                       Overviews / AI Mode and Bing Copilot answers are built from
                       THESE indexes; blocking them removes you from AI answers too.
      search        -- AI-search index crawlers (OAI-SearchBot, Claude-SearchBot,
                       PerplexityBot, ...). Allow them to stay citable.
      user          -- user-triggered live fetchers (ChatGPT-User, Claude-User,
                       Perplexity-User, ...). A person asked an assistant about you.
      training      -- model-training collectors and control tokens (GPTBot,
                       ClaudeBot, Google-Extended, Applebot-Extended, CCBot, ...).
                       Blocking them is a legitimate opt-out that does not hurt
                       citability.
  * a "core" flag per token: the stance of a class is computed over its core
    tokens (stable, widely-documented ones) so a verdict does not swing every time
    a minor crawler appears; non-core tokens are still reported.
  * an RFC 9309 robots.txt evaluator: groups merge per product token, the most
    specific matching group wins over '*', longest-path match decides, Allow wins a
    tie, '*' and '$' wildcards are honored.

Usage:
  python3 ai_crawlers.py --robots robots.txt [--path /pricing] [--human]
  python3 ai_crawlers.py --list [--human]
  python3 ai_crawlers.py --generate citable-no-training [--sitemap https://site.com/sitemap.xml]

Standard library only. Deterministic. No network (callers fetch robots.txt).
"""
import argparse
import json
import re
import sys

# token, operator, class, core, purpose
_REGISTRY = [
    # classic search engines -- the index AI Overviews / AI Mode / Copilot draw from
    ("Googlebot", "Google", "search_engine", True,
     "Google Search index; also the source for AI Overviews and AI Mode"),
    ("Bingbot", "Microsoft", "search_engine", True,
     "Bing index; also grounds Copilot answers and many third-party AI engines"),
    # AI-search index crawlers
    ("OAI-SearchBot", "OpenAI", "search", True, "ChatGPT search index"),
    ("Claude-SearchBot", "Anthropic", "search", True, "Claude search index"),
    ("PerplexityBot", "Perplexity", "search", True, "Perplexity answer index"),
    ("DuckAssistBot", "DuckDuckGo", "search", False, "DuckAssist answer retrieval"),
    ("Amazonbot", "Amazon", "search", False, "Alexa / Amazon answer retrieval"),
    # user-triggered live fetchers
    ("ChatGPT-User", "OpenAI", "user", True, "live fetch when a ChatGPT user asks"),
    ("Claude-User", "Anthropic", "user", True, "live fetch when a Claude user asks"),
    ("Perplexity-User", "Perplexity", "user", True, "live fetch when a Perplexity user asks"),
    ("MistralAI-User", "Mistral", "user", False, "live fetch for Le Chat users"),
    ("Meta-ExternalFetcher", "Meta", "user", False, "live fetch for Meta AI users"),
    # training collectors + training-control tokens
    ("GPTBot", "OpenAI", "training", True, "OpenAI model training"),
    ("ClaudeBot", "Anthropic", "training", True, "Anthropic model training"),
    ("Google-Extended", "Google", "training", True,
     "control token: Gemini training/grounding use; does NOT affect AI Overviews/AI Mode"),
    ("CCBot", "Common Crawl", "training", True, "open web corpus widely used for training"),
    ("Applebot-Extended", "Apple", "training", False,
     "control token: Apple model training use of Applebot-crawled content"),
    ("Meta-ExternalAgent", "Meta", "training", False, "Meta model training"),
    ("Bytespider", "ByteDance", "training", False, "ByteDance model training"),
    ("cohere-training-data-crawler", "Cohere", "training", False, "Cohere model training"),
]

CLASSES = ("search_engine", "search", "user", "training")

CRAWLERS = [
    {"token": t, "operator": o, "class": c, "core": core, "purpose": p}
    for t, o, c, core, p in _REGISTRY
]


def tokens(cls, core_only=False):
    """Tokens of one class, registry order. core_only limits to the stance-deciding set."""
    return [c["token"] for c in CRAWLERS
            if c["class"] == cls and (c["core"] or not core_only)]


# Back-compat views used by older callers.
TRAINING_BOTS = tokens("training", core_only=True)
RETRIEVAL_BOTS = tokens("search", core_only=True)
USER_BOTS = tokens("user", core_only=True)
SEARCH_ENGINE_BOTS = tokens("search_engine", core_only=True)


# --- RFC 9309 robots.txt parsing ---------------------------------------------

def parse_robots(text):
    """Parse robots.txt into groups: [{"agents": set(lower), "rules": [(allow, path)]}].
    Consecutive User-agent lines open one group; a User-agent after rules opens the next.
    Non-group lines (Sitemap, Crawl-delay, unknown) and blank lines never split a group.
    Also returns the Sitemap URLs. Tolerant: never raises on junk input."""
    groups, sitemaps = [], []
    cur, in_rules = None, False
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if cur is None or in_rules:
                cur = {"agents": set(), "rules": []}
                groups.append(cur)
                in_rules = False
            if value:
                cur["agents"].add(value.lower())
        elif field in ("allow", "disallow"):
            if cur is None:          # rule before any User-agent: ignored per RFC 9309
                continue
            in_rules = True
            if value or field == "allow":
                cur["rules"].append((field == "allow", value))
            # an empty Disallow means "allow everything" -> contributes no rule
        elif field == "sitemap" and value:
            sitemaps.append(value)
    return groups, sitemaps


def _rules_for(token, groups):
    """Merged rules for `token`: every group naming the token (case-insensitive product
    token) is combined; if none names it, every '*' group is combined. Returns
    (rules, matched_by) where matched_by is 'specific' | 'wildcard' | None."""
    t = token.lower()
    specific = [g for g in groups if t in g["agents"]]
    if specific:
        return [r for g in specific for r in g["rules"]], "specific"
    star = [g for g in groups if "*" in g["agents"]]
    if star:
        return [r for g in star for r in g["rules"]], "wildcard"
    return [], None


def _pattern_regex(pattern):
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
    return re.compile("^" + rx + ("$" if anchored else ""))


def path_allowed(rules, path="/"):
    """RFC 9309 decision: the longest matching rule wins; on equal length Allow wins;
    no matching rule -> allowed."""
    best_len, best_allow = -1, True
    for allow, pat in rules:
        if not pat.startswith("/") and not pat.startswith("*"):
            continue                 # malformed path; ignore rather than guess
        if _pattern_regex(pat).match(path):
            n = len(pat)
            if n > best_len or (n == best_len and allow):
                best_len, best_allow = n, allow
    return best_allow


def bot_status(token, groups, path="/"):
    """'blocked' | 'allowed' | 'unmentioned' for one token at `path`."""
    rules, matched = _rules_for(token, groups)
    if matched is None:
        return "unmentioned"
    return "allowed" if path_allowed(rules, path) else "blocked"


def _stance(statuses):
    blocked = [b for b, s in statuses.items() if s == "blocked"]
    if statuses and len(blocked) == len(statuses):
        return "blocked"
    return "partial" if blocked else "open"


def classify(text, path="/"):
    """Full per-class policy read of a robots.txt at `path`. Deterministic."""
    groups, sitemaps = parse_robots(text)
    out = {"path": path, "classes": {}, "sitemaps": sitemaps}
    for cls in CLASSES:
        core = {b: bot_status(b, groups, path) for b in tokens(cls, core_only=True)}
        extra = {b: bot_status(b, groups, path) for b in tokens(cls)
                 if b not in core}
        allb = dict(core, **extra)
        out["classes"][cls] = {
            "stance": _stance(core),
            "allowed": [b for b, s in allb.items() if s != "blocked"],
            "blocked": [b for b, s in allb.items() if s == "blocked"],
            "explicitly_named": [b for b in allb
                                 if any(b.lower() in g["agents"] for g in groups)],
        }
    return out


_NOTES = {
    "search-engine-blocked": (
        "Googlebot or Bingbot is blocked -- this removes the site from classic search AND "
        "from AI Overviews / AI Mode / Copilot answers built on those indexes. Fix first."),
    "retrieval-blocked": (
        "AI-search crawlers are disallowed -- the site is opting OUT of AI-answer citation. "
        "Allow OAI-SearchBot / Claude-SearchBot / PerplexityBot to stay citable."),
    "retrieval-partial": (
        "Some AI-search crawlers are blocked -- citation coverage is uneven across answer "
        "engines. Allow every AI-search crawler you want to be cited by."),
    "citable-training-blocked": (
        "Best-practice posture: AI-search crawlers allowed (citable) while training "
        "crawlers are blocked (opted out of model training)."),
    "citable-training-partial": (
        "AI-search is open; training is blocked for some crawlers only -- decide "
        "explicitly per training token."),
    "fully-open": "All AI crawlers -- search, user-triggered and training -- are allowed.",
}


def verdict(text, path="/"):
    """Headline verdict + note over classify(). Precedence: a blocked classic search
    engine outranks everything (it silently kills AI-answer visibility too)."""
    c = classify(text, path)
    se = c["classes"]["search_engine"]["stance"]
    rs = c["classes"]["search"]["stance"]
    ts = c["classes"]["training"]["stance"]
    if se != "open":
        v = "search-engine-blocked"
    elif rs == "blocked":
        v = "retrieval-blocked"
    elif rs == "partial":
        v = "retrieval-partial"
    elif ts == "blocked":
        v = "citable-training-blocked"
    elif ts == "partial":
        v = "citable-training-partial"
    else:
        v = "fully-open"
    notes = [_NOTES[v]]
    if c["classes"]["user"]["stance"] != "open":
        notes.append("User-triggered fetchers (" + ", ".join(c["classes"]["user"]["blocked"])
                     + ") are blocked -- assistants cannot read the page when a person "
                     "asks about it.")
    if "Google-Extended" in c["classes"]["training"]["blocked"]:
        notes.append("Google-Extended only governs Gemini training/grounding use; it does "
                     "not remove pages from AI Overviews or AI Mode (Googlebot does).")
    c.update({"verdict": v, "note": " ".join(notes)})
    return c


# --- robots.txt policy generator ---------------------------------------------

POLICIES = {
    "citable-no-training": "allow search engines + AI search + user fetchers; block training",
    "fully-open": "allow every crawler",
    "search-only": "allow classic search engines only; block every AI crawler class",
}


def generate(policy, sitemap=None):
    """Emit a robots.txt AI-policy block for a named posture. Deterministic."""
    if policy not in POLICIES:
        raise ValueError("unknown policy %r (choose: %s)" % (policy, ", ".join(POLICIES)))
    lines = ["# AI crawler policy: %s -- %s" % (policy, POLICIES[policy]), ""]
    if policy == "citable-no-training":
        blocked = tokens("training")
        allowed = tokens("search") + tokens("user")
    elif policy == "search-only":
        blocked = tokens("training") + tokens("search") + tokens("user")
        allowed = []
    else:
        blocked, allowed = [], []
    if allowed:
        lines += ["User-agent: %s" % t for t in allowed] + ["Allow: /", ""]
    if blocked:
        lines += ["User-agent: %s" % t for t in blocked] + ["Disallow: /", ""]
    lines += ["User-agent: *", "Allow: /", ""]
    if sitemap:
        lines.append("Sitemap: %s" % sitemap)
    return "\n".join(lines).rstrip() + "\n"


# --- CLI ----------------------------------------------------------------------

def _human(v):
    print("AI crawler verdict: %s  (path %s)" % (v["verdict"], v["path"]))
    print("  " + v["note"])
    for cls in CLASSES:
        c = v["classes"][cls]
        print("  - %-13s %-8s blocked=%s" % (cls, c["stance"], ", ".join(c["blocked"]) or "none"))
    if v["sitemaps"]:
        print("  sitemaps: " + ", ".join(v["sitemaps"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI-crawler registry + robots.txt policy")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--robots", help="robots.txt file to judge")
    g.add_argument("--list", action="store_true", help="print the crawler registry")
    g.add_argument("--generate", metavar="POLICY", help="emit a robots.txt policy block: "
                   + ", ".join(POLICIES))
    ap.add_argument("--path", default="/", help="URL path to evaluate (default /)")
    ap.add_argument("--sitemap", help="Sitemap URL to append when generating")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)

    if a.list:
        if a.human:
            for c in CRAWLERS:
                print("%-30s %-12s %-13s %s" % (c["token"], c["operator"], c["class"],
                                               "core" if c["core"] else "-"))
        else:
            print(json.dumps(CRAWLERS, indent=2))
        return 0
    if a.generate:
        try:
            sys.stdout.write(generate(a.generate, a.sitemap))
        except ValueError as e:
            print(json.dumps({"error": str(e)}))
            return 2
        return 0
    try:
        with open(a.robots, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        print(json.dumps({"error": "could not read robots file: %s" % e}))
        return 2
    v = verdict(text, a.path)
    if a.human:
        _human(v)
    else:
        print(json.dumps(v, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
