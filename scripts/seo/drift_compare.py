#!/usr/bin/env python3
"""drift_compare.py -- compare a fresh capture against a STORED SQLite baseline.

Captures the current SEO-element snapshot (via the canonical `drift_tools.capture()` over
the SSRF-guarded `drift_tools.load_html()`), resolves a stored baseline from the SQLite
store (by `--baseline-id`, else latest `--label`, else latest `--url`, else latest overall),
and runs the `drift_severity` engine to produce a severity-ranked change report.

Reuses the store helpers in drift_baseline.py so the schema lives in one place; reuses the
severity rules in drift_severity.py so the change->tier mapping lives in one place.

Standard library only. Deterministic; works fully offline.

Usage:
  drift_compare.py --file page.html --db baselines.db --url https://site.com/
  drift_compare.py --file page.html --db baselines.db --baseline-id 7
  drift_compare.py --url https://site.com/ --db baselines.db --label prod
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drift_tools     # noqa: E402  (canonical capturer + SSRF-guarded loader)
import drift_baseline  # noqa: E402  (the shared SQLite store)
import drift_severity  # noqa: E402  (the change->severity engine)


class _JsonArgParser(argparse.ArgumentParser):
    """argparse's own failures (a missing required arg, a bad type/choice) must honor the
    JSON-error contract too: emit {"error": ...} to stdout + a non-zero exit, never a bare
    usage dump to stderr. stdlib + ASCII."""
    def error(self, message):
        msg = str(message).encode("ascii", "replace").decode("ascii")
        print(json.dumps({"error": msg}))
        sys.exit(2)


def _human(result, baseline_id, captured_at):
    head = "Compared against baseline #%s (captured %s): %s" % (
        baseline_id, captured_at, result["summary"])
    lines = [head]
    for c in result["regressions"]:
        lines.append("  [%s] %-16s %r -> %r  (%s)"
                     % (c["severity"].upper(), c["element"], c["before"], c["after"], c["code"]))
    return "\n".join(lines).encode("ascii", "replace").decode("ascii")


def main(argv=None):
    ap = _JsonArgParser(description="Compare a fresh capture against a stored SEO baseline.")
    ap.add_argument("--file", help="local HTML file")
    ap.add_argument("--url", help="page URL (fetched through the shared SSRF guard); also selects the baseline")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--robots", help="robots.txt file: also snapshot the AI-crawler verdict (rule D15)")
    ap.add_argument("--db", help="SQLite store path (default: <cwd>/.seo-drift/baselines.db; "
                                 "refuses to default inside the plugin root)")
    ap.add_argument("--baseline-id", type=int, help="compare against this exact stored baseline id")
    ap.add_argument("--label", help="compare against the latest baseline carrying this label")
    ap.add_argument("--word-noise", type=float, default=drift_severity.WORD_NOISE)
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args(argv)

    try:
        db_path = args.db or drift_baseline.default_db_path()
    except drift_baseline.PluginRootError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    if not os.path.exists(db_path):
        print(json.dumps({"error": "no baseline store at %s -- run drift_baseline.py first" % db_path}))
        return 1

    html, err = drift_tools.load_html(args.file, args.url, args.no_network)
    if err and not html:
        print(json.dumps({"error": err}))
        return 1
    robots = None
    if args.robots:
        try:
            with open(args.robots, encoding="utf-8", errors="replace") as fh:
                robots = fh.read()
        except OSError as e:
            print(json.dumps({"error": "could not read --robots %s: %s" % (args.robots, e)}))
            return 1
    current = drift_tools.capture(html, args.url, robots)

    try:
        conn = drift_baseline.connect(db_path, create=False)
    except (OSError, sqlite3.Error) as e:
        print(json.dumps({"error": "could not open store %s: %s" % (db_path, e)}))
        return 1
    try:
        row = drift_baseline.get_baseline(conn, baseline_id=args.baseline_id,
                                          label=args.label, url=args.url)
    except sqlite3.Error as e:
        print(json.dumps({"error": "could not read baseline: %s" % e}))
        return 1
    finally:
        conn.close()

    if row is None:
        sel = ("id=%s" % args.baseline_id if args.baseline_id is not None
               else "label=%r" % args.label if args.label
               else "url=%r" % args.url if args.url else "latest")
        print(json.dumps({"error": "no stored baseline matches %s in %s" % (sel, db_path)}))
        return 1

    baseline = drift_baseline.row_snapshot(row)
    result = drift_severity.evaluate(baseline, current, word_noise=args.word_noise)
    result["baseline_id"] = row["id"]
    result["baseline_captured_at"] = row["captured_at"]
    result["url"] = args.url or row["url"]
    if args.human:
        print(_human(result, row["id"], row["captured_at"]))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
