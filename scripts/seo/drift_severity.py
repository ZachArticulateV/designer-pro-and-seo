#!/usr/bin/env python3
"""drift_severity.py -- the seo-drift change->severity engine.

A deterministic, stdlib-only severity model for on-page SEO drift. Its rules are
DERIVED FROM EXACTLY which elements `drift_tools.capture()` already records -- nothing
else. Every captured field maps to one numbered rule (D1..D15) in one of three tiers:

    critical  -- a change that can DE-INDEX the page or hand its ranking signals to a
                 different URL (robots noindex/nofollow gained; canonical flipped or
                 dropped). Fix before anything else.
    high      -- a change to a PRIMARY on-page relevance signal Google weights heavily
                 (title, h1, structured-data loss, a robots directive otherwise lost).
    advisory  -- a change to a SECONDARY signal, or one that is usually intentional
                 (meta description, Open Graph, h2 structure, schema added, canonical
                 added, word-count drift beyond the noise floor).

The three-tier shape is a generic idea; the change->tier *mapping* and the wording,
numbering, and thresholds below are our own, authored from this plugin's captured-element
list with no external comparison-rule source consulted. See
`references/seo-drift/severity-model.md` for the full rationale and worked examples.

Importable:  evaluate(baseline_snapshot, current_snapshot, word_noise=0.20) -> dict
CLI:         drift_severity.py --baseline base.json --current cur.json [--human]
"""
import argparse
import json
import sys

# Three tiers, most-urgent first. Used for the stable sort and the per-tier tally.
SEVERITY_ORDER = {"critical": 0, "high": 1, "advisory": 2}
# ai_crawlers verdicts ranked by how much search / AI-search visibility they remove.
VERDICT_RANK = {"fully-open": 0, "citable-training-partial": 0, "citable-training-blocked": 0,
                "retrieval-partial": 1, "retrieval-blocked": 2, "search-engine-blocked": 3}

# Word-count noise floor (fraction of the baseline count). A body-text change within
# +-WORD_NOISE of the baseline is ordinary editing churn, not drift, and is suppressed.
WORD_NOISE = 0.20

# Robots directives that, when newly ASSERTED, are index/equity-destroying.
_ROBOTS_CRITICAL = ("noindex", "nofollow", "none")


class _JsonArgParser(argparse.ArgumentParser):
    """argparse's own failures (a missing required arg, a bad type/choice) must honor the
    JSON-error contract too: emit {"error": ...} to stdout + a non-zero exit, never a bare
    usage dump to stderr. stdlib + ASCII."""
    def error(self, message):
        msg = str(message).encode("ascii", "replace").decode("ascii")
        print(json.dumps({"error": msg}))
        sys.exit(2)


def _robots_tokens(value):
    """Lowercased directive set from a meta-robots content string. `none` expands to
    its two-directive meaning (noindex + nofollow) so a switch to `none` is caught."""
    if not value:
        return set()
    raw = {t.strip().lower() for chunk in str(value).split(",") for t in chunk.split()}
    raw.discard("")
    if "none" in raw:
        raw |= {"noindex", "nofollow"}
    return raw


def _as_int(v):
    return v if isinstance(v, int) else None


def evaluate(baseline, current, word_noise=WORD_NOISE):
    """Compare two captured snapshots and return the severity-ranked change report.

    Returns a dict: {action, changed, regressions:[{element,code,severity,before,after,
    note}], counts:{critical,high,advisory}, summary}. Deterministic and side-effect
    free. Unknown/extra keys in either snapshot are ignored; only the captured-element
    rules below fire."""
    changes = []

    def add(element, code, severity, before, after, note):
        changes.append({"element": element, "code": code, "severity": severity,
                        "before": before, "after": after, "note": note})

    # --- meta_robots (D1/D2/D8) -- the only de-indexing lever on the page ----------
    rb, rc = baseline.get("meta_robots"), current.get("meta_robots")
    if rb != rc:
        gained = _robots_tokens(rc) - _robots_tokens(rb)
        if "noindex" in gained:
            add("meta_robots", "D1", "critical", rb, rc,
                "Page now asserts noindex -- it can be dropped from the search index.")
        elif "nofollow" in gained:
            add("meta_robots", "D2", "critical", rb, rc,
                "Page now asserts nofollow -- internal link equity stops flowing out.")
        else:
            add("meta_robots", "D8", "high", rb, rc,
                "Robots directive changed (no noindex/nofollow gained) -- confirm intent.")

    # --- canonical (D3/D4/D10) -- which URL owns the ranking signals ---------------
    cb, cc = baseline.get("canonical"), current.get("canonical")
    if cb != cc:
        if cb and cc:
            add("canonical", "D3", "critical", cb, cc,
                "Canonical now points to a different URL -- ranking signals reassigned.")
        elif cb and not cc:
            add("canonical", "D4", "critical", cb, cc,
                "Canonical removed -- self-reference lost; duplicate-content risk.")
        else:  # not cb and cc
            add("canonical", "D10", "advisory", cb, cc,
                "Canonical added where none existed -- usually an intentional self-canonical.")

    # --- title (D5) / h1 (D6) -- the primary relevance signals ---------------------
    if baseline.get("title") != current.get("title"):
        add("title", "D5", "high", baseline.get("title"), current.get("title"),
            "Title tag changed or removed -- the strongest on-page relevance signal.")
    if baseline.get("h1") != current.get("h1"):
        add("h1", "D6", "high", baseline.get("h1"), current.get("h1"),
            "H1 changed or removed -- the page's primary heading signal.")

    # --- schema_blocks (D7 loss / D11 gain) ----------------------------------------
    sb, sc = _as_int(baseline.get("schema_blocks")), _as_int(current.get("schema_blocks"))
    if sb is not None and sc is not None and sb != sc:
        if sc < sb:
            add("schema_blocks", "D7", "high", sb, sc,
                "Structured-data block(s) removed -- rich-result eligibility lost.")
        else:
            add("schema_blocks", "D11", "advisory", sb, sc,
                "Structured-data block(s) added -- verify the markup validates.")

    # --- secondary signals: meta description (D9), Open Graph (D12), h2s (D13) ------
    if baseline.get("meta_description") != current.get("meta_description"):
        add("meta_description", "D9", "advisory",
            baseline.get("meta_description"), current.get("meta_description"),
            "Meta description changed -- affects SERP snippet, not ranking directly.")
    for og in ("og_title", "og_description", "og_image"):
        if baseline.get(og) != current.get(og):
            add(og, "D12", "advisory", baseline.get(og), current.get(og),
                "Open Graph %s changed -- affects social/share presentation." % og[3:])
    hb, hc = _as_int(baseline.get("h2_count")), _as_int(current.get("h2_count"))
    if hb is not None and hc is not None and hb != hc:
        add("h2_count", "D13", "advisory", hb, hc,
            "H2 count changed -- the page's subsection structure shifted.")

    # --- word_count (D14) -- suppressed within the noise floor ---------------------
    wb, wc = _as_int(baseline.get("word_count")), _as_int(current.get("word_count"))
    if wb is not None and wc is not None and wb != wc:
        ratio = abs(wc - wb) / max(1, wb)
        if ratio > word_noise:
            add("word_count", "D14", "advisory", wb, wc,
                "Body word count moved %d%% (> %d%% noise floor) -- content materially changed."
                % (round(ratio * 100), round(word_noise * 100)))

    # --- ai_crawler_verdict (D15) -- robots.txt AI/search visibility ---------------
    ab, ac = baseline.get("ai_crawler_verdict"), current.get("ai_crawler_verdict")
    if ab is not None and ac is not None and ab != ac:
        rb_, rc_ = VERDICT_RANK.get(ab, 0), VERDICT_RANK.get(ac, 0)
        if rc_ > rb_:
            tier = "critical" if rc_ >= VERDICT_RANK["retrieval-blocked"] else "high"
            add("ai_crawler_verdict", "D15", tier, ab, ac,
                "robots.txt now blocks more of search / AI search -- %s. Citation and "
                "AI Overview visibility can vanish without any on-page change." % ac)
        else:
            add("ai_crawler_verdict", "D15", "advisory", ab, ac,
                "AI-crawler policy changed without reducing search / AI-search access "
                "(e.g. training bots newly blocked or allowed) -- confirm intent.")

    changes.sort(key=lambda c: (SEVERITY_ORDER.get(c["severity"], 9), c["element"]))
    counts = {tier: sum(1 for c in changes if c["severity"] == tier)
              for tier in ("critical", "high", "advisory")}
    summary = ("no SEO drift detected" if not changes
               else "%d element(s) drifted since baseline (%d critical, %d high, %d advisory)"
               % (len(changes), counts["critical"], counts["high"], counts["advisory"]))
    return {"action": "compare", "changed": len(changes), "regressions": changes,
            "counts": counts, "summary": summary}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _human(result):
    lines = [result["summary"]]
    for c in result["regressions"]:
        lines.append("  [%s] %-16s %s  (%s)"
                     % (c["severity"].upper(), c["element"], c["note"], c["code"]))
    return "\n".join(lines).encode("ascii", "replace").decode("ascii")


def main(argv=None):
    ap = _JsonArgParser(description="Severity-classify drift between two captured snapshots.")
    ap.add_argument("--baseline", required=True, help="baseline snapshot JSON (from drift_baseline)")
    ap.add_argument("--current", required=True, help="current snapshot JSON")
    ap.add_argument("--word-noise", type=float, default=WORD_NOISE)
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args(argv)
    try:
        base, cur = _load(args.baseline), _load(args.current)
    except (OSError, ValueError) as e:
        print(json.dumps({"error": "could not read snapshot JSON: %s" % e}))
        return 1
    result = evaluate(base, cur, word_noise=args.word_noise)
    print(_human(result) if args.human else json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
