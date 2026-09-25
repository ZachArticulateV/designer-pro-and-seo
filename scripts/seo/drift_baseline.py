#!/usr/bin/env python3
"""drift_baseline.py -- capture an SEO-element snapshot and store it in a local SQLite db.

The persistence layer of the seo-drift engine ("git for SEO"). It reuses
`drift_tools.capture()` as the one canonical element capturer and `drift_tools.load_html()`
as the one SSRF-guarded loader (local `--file`, or `--url` fetched through the shared
`net_safety.safe_open` guard -- never a raw urlopen), then writes the snapshot into a
SQLite database under the user's workspace.

This module is ALSO the shared store: drift_compare.py and drift_history.py import its
connect/insert/get/list helpers so the schema lives in exactly one place. See
`references/seo-drift/sqlite-schema.md` for the schema rationale (JSON-blob snapshot +
indexed metadata columns + a meta/version table).

Standard library only. Deterministic given `--captured-at`; works fully offline.

Usage:
  drift_baseline.py --file page.html --db baselines.db [--url https://...] [--label prod]
  drift_baseline.py --url https://site.com/ --db baselines.db --label prod
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

# scripts/seo is on sys.path[0] when run as a script and is added by the tests; this also
# makes drift_tools importable when this module is imported by drift_compare/history.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drift_tools  # noqa: E402  (the canonical capturer + SSRF-guarded loader)

SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS baselines (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT,
    label         TEXT,
    captured_at   TEXT NOT NULL,
    snapshot_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_baselines_url   ON baselines(url);
CREATE INDEX IF NOT EXISTS ix_baselines_label ON baselines(label);
"""


class _JsonArgParser(argparse.ArgumentParser):
    """argparse's own failures (a missing required arg, a bad type/choice) must honor the
    JSON-error contract too: emit {"error": ...} to stdout + a non-zero exit, never a bare
    usage dump to stderr. stdlib + ASCII."""
    def error(self, message):
        msg = str(message).encode("ascii", "replace").decode("ascii")
        print(json.dumps({"error": msg}))
        sys.exit(2)


class PluginRootError(Exception):
    """The cwd looks like the plugin's OWN root; refuse to put the store inside the plugin."""


def _is_plugin_root(path):
    """A cwd is the plugin root when it carries the plugin-manifest layout -- a
    `.claude-plugin/` directory, or a `plugin.json` at the top. The drift store must never
    be written inside the plugin (the contract: baselines live under the USER's workspace)."""
    return (os.path.isdir(os.path.join(path, ".claude-plugin"))
            or os.path.isfile(os.path.join(path, "plugin.json"))
            or os.path.isfile(os.path.join(path, ".claude-plugin", "plugin.json")))


def default_db_path():
    """Default store: `<cwd>/.seo-drift/baselines.db` under the user's workspace. If the cwd
    is the plugin's OWN root (a `.claude-plugin/` dir or `plugin.json` is present), raise
    PluginRootError so the caller must pass an explicit --db under their workspace -- the
    store is never created inside the plugin. drift_compare / drift_history share this guard."""
    cwd = os.getcwd()
    if _is_plugin_root(cwd):
        raise PluginRootError(
            "refusing to use a drift store inside the plugin directory (%s); "
            "pass --db PATH under your own workspace" % cwd)
    return os.path.join(cwd, ".seo-drift", "baselines.db")


def connect(db_path, create=True):
    """Open (and, when create=True, initialize) the SQLite store. Raises FileNotFoundError
    when create=False and the db file is absent -- callers turn that into a JSON error."""
    if not create and not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    parent = os.path.dirname(os.path.abspath(db_path))
    if create and parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if create:
        init_schema(conn)
    return conn


def init_schema(conn):
    conn.executescript(_DDL)
    if conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone() is None:
        conn.execute("INSERT INTO meta(key, value) VALUES('schema_version', ?)",
                     (str(SCHEMA_VERSION),))
    conn.commit()


def insert_baseline(conn, url, label, captured_at, snapshot):
    cur = conn.execute(
        "INSERT INTO baselines(url, label, captured_at, snapshot_json) VALUES(?,?,?,?)",
        (url, label, captured_at, json.dumps(snapshot, sort_keys=True)))
    conn.commit()
    return cur.lastrowid


def get_baseline(conn, baseline_id=None, label=None, url=None):
    """Resolve ONE stored baseline: by explicit id, else the latest for a label, else the
    latest for a url, else the latest overall. 'latest' = max captured_at, id as tiebreak.
    Returns an sqlite3.Row or None."""
    if baseline_id is not None:
        return conn.execute("SELECT * FROM baselines WHERE id=?", (baseline_id,)).fetchone()
    if label:
        return conn.execute(
            "SELECT * FROM baselines WHERE label=? ORDER BY captured_at DESC, id DESC LIMIT 1",
            (label,)).fetchone()
    if url:
        return conn.execute(
            "SELECT * FROM baselines WHERE url=? ORDER BY captured_at DESC, id DESC LIMIT 1",
            (url,)).fetchone()
    return conn.execute(
        "SELECT * FROM baselines ORDER BY captured_at DESC, id DESC LIMIT 1").fetchone()


def list_baselines(conn, url=None, label=None):
    """All stored baselines (optionally filtered by url and/or label), oldest first."""
    clauses, params = [], []
    if url:
        clauses.append("url=?")
        params.append(url)
    if label:
        clauses.append("label=?")
        params.append(label)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return conn.execute(
        "SELECT * FROM baselines%s ORDER BY captured_at ASC, id ASC" % where, params).fetchall()


def row_snapshot(row):
    return json.loads(row["snapshot_json"])


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main(argv=None):
    ap = _JsonArgParser(description="Capture an SEO-element snapshot into a SQLite baseline store.")
    ap.add_argument("--capture", action="store_true", help="capture a baseline (the default action)")
    ap.add_argument("--file", help="local HTML file")
    ap.add_argument("--url", help="page URL (fetched through the shared SSRF guard)")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--robots", help="robots.txt file: also snapshot the AI-crawler verdict (rule D15)")
    ap.add_argument("--db", help="SQLite store path (default: <cwd>/.seo-drift/baselines.db; "
                                 "refuses to default inside the plugin root)")
    ap.add_argument("--label", help="optional label for this snapshot (e.g. 'prod', 'pre-deploy')")
    ap.add_argument("--captured-at", help="ISO timestamp override (default: now, UTC) -- set for reproducible tests")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args(argv)

    # Resolve the store path first so we refuse a plugin-internal default before any work.
    try:
        db_path = args.db or default_db_path()
    except PluginRootError as e:
        print(json.dumps({"error": str(e)}))
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
    snapshot = drift_tools.capture(html, args.url, robots)
    captured_at = args.captured_at or _now_iso()
    try:
        conn = connect(db_path, create=True)
    except (OSError, sqlite3.Error) as e:
        print(json.dumps({"error": "could not open store %s: %s" % (db_path, e)}))
        return 1
    try:
        rowid = insert_baseline(conn, args.url, args.label, captured_at, snapshot)
    except sqlite3.Error as e:
        print(json.dumps({"error": "could not write baseline: %s" % e}))
        return 1
    finally:
        conn.close()

    result = {"action": "baseline", "db": db_path, "id": rowid, "url": args.url,
              "label": args.label, "captured_at": captured_at, "snapshot": snapshot}
    if args.human:
        print(("Stored baseline #%d (%s) at %s -> %s"
               % (rowid, args.label or "no label", captured_at, db_path)
               ).encode("ascii", "replace").decode("ascii"))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
