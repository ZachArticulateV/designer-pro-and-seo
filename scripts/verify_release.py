#!/usr/bin/env python3
"""
verify_release.py — the single release gate for the designer-pro-and-seo plugin.

Aggregates the checks that keep the published plugin honest and consistent, and
exits non-zero on any failure so CI (and a pre-publish run) can block a bad release.
Standard library only. ASCII-only output (safe on a Windows cp1252 console).

Checks:
  1. smoke    — scripts/smoke_test.py passes; docs cite the current smoke count
  2. refs     — every scripts/...py path named in a SKILL.md exists; no singular
                "extension/" path typo
  3. prov     — every shipped script has a record in references/PROVENANCE.md
  4. clean    — no name from a local .clean-room-denylist appears in any shipped file
  5. config   — no @latest in any .mcp.json; plugin.json homepage/repository set and
                license non-placeholder + consistent with the LICENSE file
  6. counts   — SHIPPING + README skill counts match the filesystem; README states
                the real script count
  7. version  — README/SHIPPING/RELEASE-NOTES reference the current version; no stale
                version pointer remains in any skill
  8. paths    — skills invoke bundled scripts via ${CLAUDE_PLUGIN_ROOT}, not a bare
                'python scripts/...' path (which breaks once the plugin is installed)
  9. market   — .claude-plugin/marketplace.json exists, has a plugin with a source,
                and its version matches plugin.json (so the repo installs as a marketplace)

  Wave-0 clean-room / governance guards (see MASTER-PLAN sections 7.3, 7.4):
  C7 cleanroom — fail-closed clean-room guard. The GENERIC family (open-license
                attribution markers, the reserved brand token, and source-attribution
                headers of any scheme) is hardcoded and runs UNCONDITIONALLY whether or
                not the gitignored .cleanroom-thirdparty exists -- so it still fires on
                public CI where the file is absent. Only the NAME portion is best-effort:
                a missing file vacuously passes the NAME denylist (mirrors _load_denylist),
                a present-but-unreadable file is a loud FAIL. Marker / brand / source
                literals are assembled from fragments so this guard's own source never
                self-flags. NAMES (the denylist literals, plus a copyright-sign+name
                pattern) are scanned on RAW text with NO whole-file exemption -- a
                third-party name may never appear in ANY shipped file. The generic
                marker / brand / source family is exempt only in the four governance /
                attribution docs (references/PROVENANCE.md, references/NOTICE.md, the root
                NOTICE.md, references/ENGINE-CONTRACTS.md). tests/ is pruned. A span-aware
                owner-tool allowlist exempts a denylisted substring only where it sits
                inside an allowlisted token, never a standalone leak. The brand token
                matches the all-caps form as a whole word (and the title-case form only in
                "<brand> framework" context), never the bare lowercase form (which collides
                with workflow / overflow / data-flow).
  C9 sync/lock — no sync_* prompt-fetcher script anywhere; no *-prompts.lock file.
  C8 prov      — every per-class asset section exists in PROVENANCE; every
                references/shared/*.md + AGENTS.md has a row; high-risk rows carry a
                clean-room method note. Widened: EVERY references/**/*.md CITED by a
                SKILL.md (per-skill references included, extracted the C1 way) is a
                high-risk class -> must have a first-cell-anchored backtick PROVENANCE
                row AND a method note (a per-skill reference can no longer ship unrecorded).
  C1 skillrefs — every references/*.md path cited inside a SKILL.md resolves on disk.
  C-HANDOFF    — the three named handoffs hold on the current tree (qa-gate->seo-page
                and design-research->seo-cluster stay orchestrator Dependencies;
                seo-drift <-> design-visual-qa stay a Notes-level mutual reference and
                never a Dependencies edge).
  C-COUNT      — no NEW data/*.csv row count within +/-2 of a recorded inspiration
                count, nor a column-set near-match (record-only until CSVs land).
  C11 stdlib   — scripts/** import only the stdlib allowlist (+ local siblings).

  Wave-2 scaffold guards (agents/ layer + connector Tier-2; see MASTER-PLAN 7.4 / 8-W2):
  C5 agentpriv -- every agents/*.md (the _-prefixed template is excluded) declares the
                required frontmatter keys (name/description/model/maxTurns/tools) and is
                LEAST-PRIVILEGE: a fetch-only agent (holds WebFetch/WebSearch) may not
                also hold Bash, and no agent may grant a tool outside the leaf primitive
                set (so Task -- the dispatch power -- and any other high-privilege tool fail).
  C3 agentwf   -- every agent is well-formed: the '## Capability routing' section holds a
                ```capability-routing block carrying every fixed CAPABILITY-TIERS key, and
                the '## Output contract' section holds a non-empty machine-parseable
                ```output-contract block with its fixed keys -- a heading with no fenced
                block, or a block missing a required key, FAILS (no vacuous heading-only
                pass). It also names NO orchestrator as a Dependencies entry and calls NO
                other agent (no Task tool, no agents/<other>.md ref) -- a one-directional
                orchestrator->agent->script DAG. Plus a dispatch-shape guard: a fenced
                ```dispatch block (in any orchestrator SKILL.md or references/dispatch-
                matrix.md) that splits its specialists 8-always + 7-conditional FAILS
                (do-not-mirror a third-party roster). Plus name<->file<->sibling parity:
                every agents/<name>.md has frontmatter name==<name> and a sibling
                skills/<name>/SKILL.md (orphan agent or name mismatch FAILS). Orchestrator
                dispatch==disk parity is deferred to W4 (not enforced here).
  C4 tier2     -- every skill that embeds a machine-parseable ```capability-routing block
                declares a non-empty tier2 that NAMES A SCRIPT RESOLVING ON DISK (reuses
                the check_refs/_exists resolver, extended to bare basenames) AND has a
                golden example under references/examples/<skill>/ that exercises EVERY such
                script with an actual runnable COMMAND (the script basename followed by an
                argument / line-continuation) -- a bare prose mention no longer counts. A
                block carrying 'c4_exempt: true' (and seo-image-gen) is exempt.

Usage:
  python3 scripts/verify_release.py            # from anywhere
  python3 scripts/verify_release.py --root DIR # check a copy (used by self-tests)
  python3 scripts/verify_release.py --skip-smoke
"""
import argparse
import ast
import csv
import glob
import json
import os
import re
import subprocess
import sys

TEXT_EXTS = (".md", ".py", ".json", ".csv", ".txt", ".html", ".css", ".js", ".yml", ".yaml")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def skill_files(root):
    return sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))


def rel(root, path):
    return os.path.relpath(path, root).replace("\\", "/")


def _load_denylist(root):
    """Returns (names, error). Real client/brand names are kept OUT of this public repo:
    list them (one per line) in a local, gitignored `.clean-room-denylist`. A missing
    file is fine ([] names); a present-but-unreadable file is an error so the gate fails
    loudly instead of silently passing without checking."""
    path = os.path.join(root, ".clean-room-denylist")
    if not os.path.exists(path):
        return [], None
    try:
        with open(path, encoding="utf-8") as f:
            names = [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
        return names, None
    except (OSError, UnicodeDecodeError) as e:
        return [], "could not read .clean-room-denylist: %s" % e


# --- individual checks: each returns a list of (name, ok, detail) ---------------

def check_smoke(root, skip_smoke=False):
    if skip_smoke:
        return [("smoke_test passes", True, "skipped (--skip-smoke)")]
    r = subprocess.run([sys.executable, os.path.join(root, "scripts", "smoke_test.py")],
                       capture_output=True, encoding="utf-8")
    lines = (r.stdout or "").strip().splitlines()
    last = lines[-1] if lines else ((r.stderr or "")[:120])
    out = [("smoke_test passes", r.returncode == 0, last)]
    m = re.search(r"(\d+)/(\d+) checks passed", last or "")
    if m:
        total = m.group(2)
        q = read(os.path.join(root, "QUICKSTART.md"))
        out.append(("QUICKSTART cites current smoke count",
                    ("%s/%s" % (total, total)) in q, "%s/%s" % (total, total)))
    else:
        out.append(("smoke count parseable for doc check", False,
                    "could not parse 'X/Y checks passed' from smoke output"))
    return out


def check_refs(root):
    missing, ext_typo = [], []
    for sf in skill_files(root):
        txt = read(sf)
        for m in re.findall(r"scripts[\\/][A-Za-z0-9_.\\/-]+\.py", txt):
            norm = m.replace("\\", "/")
            if not os.path.exists(os.path.join(root, *norm.split("/"))):
                missing.append("%s -> %s" % (rel(root, sf), norm))
        if re.search(r"\bextension/", txt):
            ext_typo.append(rel(root, sf))
    return [
        ("SKILL.md script references all exist", not missing, "; ".join(missing) or "all exist"),
        ("no singular 'extension/' path", not ext_typo, ", ".join(ext_typo) or "none"),
    ]


def check_prov(root):
    prov = read(os.path.join(root, "references", "PROVENANCE.md"))
    scripts = [rel(root, p) for p in glob.glob(os.path.join(root, "scripts", "**", "*.py"), recursive=True)]
    # require an exact, backtick-delimited path entry (records use `scripts/.../x.py`),
    # so unrelated prose or a `foo.py.bak` cannot satisfy the check
    missing = [s for s in scripts if ("`%s`" % s) not in prov]
    return [("every shipped script has a PROVENANCE record", not missing,
             ", ".join(missing) or ("all %d recorded" % len(scripts)))]


def check_clean(root):
    # Forbidden names load from a local, gitignored .clean-room-denylist so the literal
    # names never live in this public repo. docs/ IS scanned -- it can ship publicly.
    denylist, load_err = _load_denylist(root)
    if load_err:  # present but unreadable -> fail loudly, never silently pass
        return [("clean-room: .clean-room-denylist is readable", False, load_err)]
    hits, unreadable = [], []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != ".git"]
        for fn in fns:
            if not fn.endswith(TEXT_EXTS):
                continue
            p = os.path.join(dp, fn)
            try:
                txt = read(p)
            except (OSError, UnicodeDecodeError):
                unreadable.append(rel(root, p))  # can't scan -> can't clear it
                continue
            for name in denylist:
                if name in txt:
                    hits.append("%s: %s" % (rel(root, p), name))
    detail = ("; ".join(hits) or ("clean (%d name(s) checked)" % len(denylist)
              if denylist else "clean (no .clean-room-denylist configured)"))
    return [
        ("clean-room: no denylisted names in shipped files", not hits, detail),
        ("clean-room: all shipped text files are UTF-8 readable", not unreadable,
         ", ".join(unreadable) or "all readable"),
    ]


def check_config(root):
    out = []
    latest = []
    for dp, dns, fns in os.walk(root):  # any .mcp.json anywhere, not just extensions/*
        dns[:] = [d for d in dns if d != ".git"]
        for fn in fns:
            if fn == ".mcp.json" and "@latest" in read(os.path.join(dp, fn)):
                latest.append(rel(root, os.path.join(dp, fn)))
    out.append(("no @latest in any .mcp.json", not latest, ", ".join(latest) or "none"))

    pj = json.loads(read(os.path.join(root, ".claude-plugin", "plugin.json")))
    out.append(("plugin.json homepage set", bool(pj.get("homepage")), pj.get("homepage", "") or "(empty)"))
    out.append(("plugin.json repository set", bool(pj.get("repository")), pj.get("repository", "") or "(empty)"))

    lic = (pj.get("license", "") or "").strip()
    placeholder = (not lic) or ("SEE LICENSE" in lic.upper()) or ("PLACEHOLDER" in lic.upper())
    out.append(("plugin.json license is non-placeholder", not placeholder, lic or "(empty)"))

    licfile = read(os.path.join(root, "LICENSE"))
    if lic.upper() == "MIT":
        out.append(("LICENSE file matches declared MIT", "MIT License" in licfile,
                    "MIT" if "MIT License" in licfile else "LICENSE is not MIT"))
    elif not placeholder:
        # declared a non-MIT license: at minimum require a substantial LICENSE file
        out.append(("LICENSE file is substantial for declared license",
                    len(licfile.strip()) > 400, "%d chars" % len(licfile.strip())))
    return out


def check_counts(root):
    out = []
    sfiles = skill_files(root)
    total = len(sfiles)
    stable = sum(1 for sf in sfiles if re.search(r"\*\*Status:\*\*\s*Stable\b", read(sf)))
    indev = total - stable

    shipping = read(os.path.join(root, "SHIPPING.md"))
    # anchor to the single canonical line so unrelated numbers can't be captured
    line = next((l for l in shipping.splitlines() if "Total skills:" in l), "")
    m = re.search(r"Total skills:\s*(\d+)\D+?(\d+)\D+?Stable\D+?(\d+)\D+?In development", line)
    if not m:
        out.append(("SHIPPING total-skills line parses", False, "canonical 'Total skills:' line not found"))
    else:
        st, ss, si = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ok = (st == total and ss == stable and si == indev)
        out.append(("SHIPPING counts match filesystem", ok,
                    "SHIPPING=%d/%d/%d actual(total/stable/indev)=%d/%d/%d" % (st, ss, si, total, stable, indev)))

    readme = read(os.path.join(root, "README.md"))
    want = "%d of %d skills" % (stable, total)  # specific phrase, not a bare "N of M"
    out.append(("README stable/total count matches filesystem", want in readme, "expected '%s'" % want))

    n_scripts = len(glob.glob(os.path.join(root, "scripts", "**", "*.py"), recursive=True))
    out.append(("README states the real script count", ("%d scripts" % n_scripts) in readme,
                "expected '%d scripts' (found %d .py files)" % (n_scripts, n_scripts)))
    return out


def check_version(root):
    out = []
    pj = json.loads(read(os.path.join(root, ".claude-plugin", "plugin.json")))
    v = pj.get("version", "")
    mm = ".".join(v.split(".")[:2]) if v else ""
    readme = read(os.path.join(root, "README.md"))
    shipping = read(os.path.join(root, "SHIPPING.md"))
    relnotes = read(os.path.join(root, "RELEASE-NOTES.md"))

    tag = "v" + mm  # e.g. "v0.4"
    tag_re = re.compile(r"v" + re.escape(mm) + r"(?!\d)")  # "v0.4" but not "v0.41"
    out.append(("README references current minor (%s)" % tag, bool(mm) and bool(tag_re.search(readme)), tag))
    out.append(("SHIPPING references current minor (%s)" % tag, bool(mm) and bool(tag_re.search(shipping)), tag))
    out.append(("RELEASE-NOTES has an entry for %s" % v, bool(v) and v in relnotes, v))

    stale = []
    for sf in skill_files(root):
        for badv in re.findall(r"v0\.\d+(?:\.\d+|\.x)?", read(sf)):  # v0.2, v0.2.1, v0.2.x
            mn = re.match(r"v(0\.\d+)", badv).group(1)
            if mn != mm:
                stale.append("%s:%s" % (rel(root, sf), badv))
    out.append(("no stale version pointer in skills", not stale, "; ".join(stale) or "none"))
    return out


def check_paths(root):
    """Skill bodies must invoke bundled scripts via ${CLAUDE_PLUGIN_ROOT}; a bare
    'python scripts/...' resolves to the user's cwd once the plugin is installed and
    silently fails. (Guards against regressing the install-path fix.)"""
    bad = []
    for sf in skill_files(root):
        for ln in read(sf).splitlines():
            if re.search(r"\b(?:python3?|py)\s+\.?/?scripts/", ln):
                bad.append("%s: %s" % (rel(root, sf), ln.strip()))
    return [("skills invoke scripts via ${CLAUDE_PLUGIN_ROOT} (no bare 'python scripts/')",
             not bad, "; ".join(bad) or "all skill script calls use the plugin-root var")]


def check_market(root):
    """The repo must be installable as its own single-plugin marketplace, and the
    marketplace entry's version must match plugin.json (Claude Code resolves updates
    off both)."""
    mpath = os.path.join(root, ".claude-plugin", "marketplace.json")
    if not os.path.exists(mpath):
        return [(".claude-plugin/marketplace.json exists", False,
                 "missing -- repo is not installable via /plugin marketplace add")]
    try:
        mp = json.loads(read(mpath))
    except ValueError as e:
        return [(".claude-plugin/marketplace.json parses", False, "ERROR: %s" % e)]
    if not isinstance(mp, dict) or not isinstance(mp.get("plugins"), list):
        return [("marketplace.json has a plugins array", False,
                 "top-level must be an object with a 'plugins' array")]
    plugins = [p for p in mp["plugins"] if isinstance(p, dict)]
    out = [("marketplace.json has a plugin entry", bool(plugins), "%d plugin(s)" % len(plugins))]
    if not plugins:
        return out
    pj = json.loads(read(os.path.join(root, ".claude-plugin", "plugin.json")))
    pv, pname = pj.get("version", ""), pj.get("name", "")
    entry = next((p for p in plugins if p.get("name") == pname), plugins[0])
    out.append(("marketplace plugin 'source' set", bool(entry.get("source")),
                entry.get("source", "") or "(none)"))
    out.append(("marketplace version matches plugin.json (%s)" % pv,
                entry.get("version") == pv,
                "marketplace=%s plugin=%s" % (entry.get("version"), pv)))
    return out


# --- Wave-0 clean-room / governance guards -------------------------------------
#
# All of the following are ADDITIVE (MASTER-PLAN sections 7.3/7.4). They never crash
# the gate -- a bug raises and is caught by main()'s per-check try/except, surfacing
# as a loud FAIL row. Output stays ASCII-only.

# Asset classes whose per-class section must exist in PROVENANCE (MASTER-PLAN 7.2).
PROV_ASSET_CLASSES = [
    "Scripts", "CSV data", "Per-skill references",
    "Agents", "Templates & prompt-libraries", "Connector-wirings",
]

# The 5 design-engine CSVs predate the clean-room count guard and are recorded in the
# PROVENANCE "Per-CSV records" table; C-COUNT only polices CSVs added AFTER this wave.
GRANDFATHERED_CSVS = {
    "color-palettes.csv", "font-pairings.csv", "product-types.csv",
    "ui-styles.csv", "ux-rules.csv",
}

# Fallback stdlib allowlist for C11 (MASTER-PLAN 7.4), used ONLY when
# sys.stdlib_module_names is unavailable (Python < 3.10). On 3.10+ the authoritative
# frozenset sys.stdlib_module_names is used instead (see _stdlib_root_names), which fixes
# false-positives on stdlib roots not hand-listed here (email, uuid, queue, threading, ...).
# Checked by ROOT package, so urllib.request / xml.etree.ElementTree / http.client /
# concurrent.futures resolve to urllib / xml / http / concurrent. A third-party import
# (requests, pandas, bs4, lxml, yaml, numpy, ...) is NOT in this set, so it FAILS -- which
# is the whole point.
STDLIB_ROOTS = {
    # plan's explicit "at least" list (reduced to root packages)
    "json", "os", "sys", "re", "argparse", "subprocess", "glob", "tempfile", "csv",
    "urllib", "xml", "http", "gzip", "zlib", "sqlite3", "concurrent", "difflib",
    "pathlib", "html", "datetime", "hashlib", "io", "math", "collections",
    "functools", "itertools", "textwrap",
    # stdlib roots already imported in the current scripts/** tree
    "ast", "base64", "mimetypes", "shutil", "colorsys",
    # stdlib buffer the W1a free-first backbone will reasonably reach for (all stdlib)
    "time", "typing", "string", "random", "socket", "ssl", "ipaddress",
    "unicodedata", "contextlib", "dataclasses", "enum", "copy", "statistics",
    "decimal", "fnmatch", "shlex", "platform", "traceback", "warnings", "struct",
    "unittest", "secrets", "base64", "logging", "operator", "heapq", "bisect",
    "abc", "types", "numbers", "calendar", "zoneinfo",
}


def _stdlib_root_names():
    """The authoritative set of stdlib ROOT package names for C11. Prefers the frozenset
    sys.stdlib_module_names (Python 3.10+), which lists every stdlib top-level module, so
    email / uuid / queue / threading / etc. are never false-flagged. Falls back to the
    hand-maintained STDLIB_ROOTS only when that frozenset is unavailable (Python < 3.10)."""
    names = getattr(sys, "stdlib_module_names", None)
    if names:
        # union with the hand list so anything we special-cased stays covered even if a
        # future runtime trims its frozenset
        return set(names) | set(STDLIB_ROOTS)
    return set(STDLIB_ROOTS)


def _ascii(s):
    """Force a detail string to ASCII so the gate's output stays cp1252-safe even when
    a denylist hit (which may contain a non-ASCII marker like a copyright sign) is
    echoed back."""
    try:
        return str(s).encode("ascii", "replace").decode("ascii")
    except Exception:
        return str(s)


def _load_thirdparty(root):
    """Returns (data, error). Mirrors _load_denylist exactly: a MISSING file is fine
    (None data, no error -> the dependent check vacuously passes); a present-but-
    unreadable / unparseable file is an error so the gate fails loudly instead of
    silently passing. The file is gitignored, so the literal third-party names never
    ship in the public repo."""
    path = os.path.join(root, ".cleanroom-thirdparty")
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except (OSError, UnicodeDecodeError, ValueError) as e:
        return None, "could not read .cleanroom-thirdparty: %s" % e


def _section(text, name):
    """Return the body under '## <name>' up to the next '## ' heading (or EOF)."""
    out, cap = [], False
    for ln in text.splitlines():
        s = ln.strip()
        if re.match(r"^#{2,}\s+" + re.escape(name) + r"\b", s):
            cap = True
            continue
        if cap and s.startswith("## "):
            break
        if cap:
            out.append(ln)
    return "\n".join(out)


def _csv_shape(path):
    """Return (data_row_count, [header columns]) for a CSV, BOM-tolerant."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    cols = [c.strip() for c in (rows[0] if rows else [])]
    return max(0, len(rows) - 1), cols


def _count_conflict(rows, cols, inspiration_counts):
    """C-COUNT helper. Returns a conflict string if a candidate CSV's row count lands
    within +/-2 of a recorded inspiration count OR its column set near-matches a
    recorded header set; else None. (No new CSVs exist this wave, so it never fires
    now -- it enforces the moment a new data/*.csv lands.)"""
    colset = {c.strip().lower() for c in cols if c.strip()}
    for rec in inspiration_counts or []:
        irows = rec.get("rows")
        icols = {str(c).strip().lower() for c in rec.get("columns", []) if str(c).strip()}
        if isinstance(irows, int) and abs(rows - irows) <= 2:
            return "row count %d is within +/-2 of inspiration count %d (%s)" % (
                rows, irows, rec.get("file"))
        if colset and icols:
            inter = colset & icols
            if len(inter) >= max(3, int(0.6 * min(len(colset), len(icols)))):
                return "column set near-matches inspiration headers (%s): %d shared" % (
                    rec.get("file"), len(inter))
    return None


def _dynamic_import_bindings(tree):
    """Pass 1 of the dynamic-import analysis. Returns (importlib_module_names,
    dynamic_func_names):
      * importlib_module_names -- local names bound to the importlib MODULE: the literal
        `importlib` plus any `import importlib as X` alias X (and `import importlib.sub`
        with no asname, which also binds the top-level `importlib` name).
      * dynamic_func_names -- local names bound to a dynamic-import FUNCTION via
        `from importlib import import_module [as Y]` (binds Y, default `import_module`).
    Builtin `__import__` is handled separately as ALWAYS dynamic, so it is not listed here.
    This catches aliased / from-imported bindings the old literal-only check missed:
      import importlib as il          -> il.import_module(...)        is dynamic
      from importlib import import_module      -> import_module(...)  is dynamic
      from importlib import import_module as Y -> Y(...)              is dynamic"""
    module_names = {"importlib"}
    func_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "importlib":
                    module_names.add(a.asname or "importlib")
                elif a.name.startswith("importlib.") and not a.asname:
                    module_names.add("importlib")  # binds the top-level importlib name too
        elif isinstance(node, ast.ImportFrom):
            if (node.level or 0) == 0 and node.module == "importlib":
                for a in node.names:
                    if a.name == "import_module":
                        func_names.add(a.asname or a.name)
                    elif a.name == "*":
                        # `from importlib import *` exposes import_module unqualified
                        func_names.add("import_module")
    # Propagate simple assignment aliases (one- or multi-hop) of a dynamic-import
    # function: `loader = import_module` / `load = importlib.import_module` then a later
    # `loader(...)` is still a dynamic import. Fixpoint over Assign nodes (ast.walk is not
    # source-ordered, so iterate until stable).
    assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
    changed = True
    while changed:
        changed = False
        for n in assigns:
            v = n.value
            rhs_dynamic = (
                (isinstance(v, ast.Name) and v.id in func_names)
                or (isinstance(v, ast.Attribute) and v.attr in ("import_module", "__import__")
                    and isinstance(v.value, ast.Name) and v.value.id in module_names)
            )
            if rhs_dynamic:
                for tgt in n.targets:
                    if isinstance(tgt, ast.Name) and tgt.id not in func_names:
                        func_names.add(tgt.id)
                        changed = True
    return module_names, func_names


def _is_dynamic_import_func(fn, module_names, func_names):
    """Pass 2 predicate: True if an ast.Call's func is a dynamic-import entry point given
    the bindings from pass 1. A bare Name is dynamic when it is builtin `__import__` or a
    name bound to a dynamic-import function; an Attribute is dynamic when its .attr is
    import_module / __import__ AND its value is a Name bound to the importlib module."""
    if isinstance(fn, ast.Name):
        return fn.id == "__import__" or fn.id in func_names
    if isinstance(fn, ast.Attribute) and fn.attr in ("import_module", "__import__"):
        return isinstance(fn.value, ast.Name) and fn.value.id in module_names
    # getattr(<importlib binding>, "import_module"|"__import__")(...) -- dynamic dispatch
    if (isinstance(fn, ast.Call) and isinstance(fn.func, ast.Name) and fn.func.id == "getattr"
            and len(fn.args) >= 2):
        obj, attr = fn.args[0], fn.args[1]
        if (isinstance(obj, ast.Name) and obj.id in module_names
                and isinstance(attr, ast.Constant) and attr.value in ("import_module", "__import__")):
            return True
    return False


def _imported_roots(path):
    """Return (set_of_root_packages, errors) imported by a Python file. Relative
    (from . import x) imports are treated as local and skipped. Dynamic imports are
    detected via a two-pass AST analysis (see _dynamic_import_bindings): `__import__`,
    `importlib.import_module`, and ALL aliased/from-imported variants
    (`import importlib as il; il.import_module(...)`,
    `from importlib import import_module [as Y]; import_module(...)`/`Y(...)`). For a
    string-literal module the root is checked against the stdlib like any other import; a
    non-literal/dynamic argument is reported as unverifiable (it cannot be proven
    stdlib-only and so must FAIL C11)."""
    roots, errs = set(), []
    try:
        tree = ast.parse(read(path))
    except (SyntaxError, ValueError) as e:
        return roots, ["cannot parse: %s" % e]
    module_names, func_names = _dynamic_import_bindings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import -> a sibling module, not a dependency
            if node.module:
                roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and _is_dynamic_import_func(node.func, module_names, func_names):
            arg = node.args[0] if node.args else None
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                roots.add(arg.value.split(".")[0])
            else:
                errs.append("dynamic import cannot be verified stdlib-only")
    return roots, errs


# Files that legitimately DOCUMENT or ATTRIBUTE the marker / brand / source family, so the
# GENERIC marker scan (never the NAME scan) is exempt in exactly these four governance docs.
_MARKER_EXEMPT = {
    "references/PROVENANCE.md", "references/NOTICE.md", "NOTICE.md",
    "references/ENGINE-CONTRACTS.md",
}


def _generic_marker_hits(relp, raw):
    """The fail-closed GENERIC family: open-license markers, the reserved brand token, and
    source-attribution headers (any scheme). Hardcoded -- runs whether or not the gitignored
    .cleanroom-thirdparty exists. Skipped only in the four governance/attribution docs. The
    literals are assembled from fragments so this guard's OWN source never carries a
    contiguous marker (and so never self-flags) while still matching real, contiguous
    markers in any other file."""
    if relp in _MARKER_EXEMPT:
        return []
    hits = []
    license_markers = ["CC" + " BY", "Creative" + " Commons", "Synced" + ":"]
    # reserved brand token: the all-caps form as a whole word, OR the title-case form ONLY
    # in "<brand> framework" context (so generic "Flow" / "user flow" never trip). The bare
    # lowercase form is never matched (it collides with workflow / overflow / data-flow).
    brand_re = re.compile(r"\b" + "FL" + "OW" + r"\b|\bFlow\s+[Ff]ramework\b")
    # source-attribution header: HTML-comment / hash-comment Source key, OR a prose/YAML key
    # whose value is a URL of ANY scheme (file://, s3://, https://, ...). ("Sour"+"ce" keeps
    # the literal out of this source.)
    _src = "Sour" + "ce"
    src_re = re.compile(r"(?:<!--\s*|#\s*)" + _src + r"\s*:|"
                        + _src + r"\s*:\s*[a-z][a-z0-9+.\-]*://", re.I)
    for m in license_markers:
        if m in raw:
            hits.append("%s: open-license attribution marker" % relp)
    if brand_re.search(raw):
        hits.append("%s: reserved brand token" % relp)
    if src_re.search(raw):
        hits.append("%s: source-attribution header" % relp)
    return hits


def _allow_spans(raw, allowlist):
    """All (start, end) spans covered by an occurrence of an allowlisted owner-tool token."""
    spans = []
    for tok in allowlist:
        if not tok:
            continue
        start = 0
        while True:
            i = raw.find(tok, start)
            if i < 0:
                break
            spans.append((i, i + len(tok)))
            start = i + 1
    return spans


def _name_leaks(relp, raw, denylist, allowlist):
    """Best-effort NAME scan on RAW text (no code-span stripping, no whole-file exemption):
    a denylisted literal that occurs OUTSIDE every allowlisted-token span is a leak. Span-
    aware so an allowlisted owner tool that CONTAINS a denylisted substring is exempted at
    that exact spot, while the same substring standing alone elsewhere is still caught."""
    spans = _allow_spans(raw, allowlist)
    hits = []
    for name in denylist:
        start = 0
        while True:
            i = raw.find(name, start)
            if i < 0:
                break
            s, e = i, i + len(name)
            if not any(a <= s and e <= b for (a, b) in spans):
                hits.append("%s: denylisted name '%s'" % (relp, name))
                break  # one finding per name per file is enough
            start = i + 1
    return hits


def check_cleanroom_thirdparty(root):
    """C7 -- third-party names / license markers / source-attribution headers.

    The GENERIC marker / brand / source family is fail-closed and runs on every shipped file
    UNCONDITIONALLY (even when .cleanroom-thirdparty is absent, e.g. public CI). Only the
    NAME portion (the denylist literals + a copyright-sign+name pattern) is best-effort: a
    missing file vacuously passes the NAME portion (mirrors _load_denylist); a present-but-
    unreadable file fails loud. NAMES are scanned on raw text with NO whole-file exemption."""
    data, err = _load_thirdparty(root)
    if err:
        return [("C7 cleanroom: .cleanroom-thirdparty is readable/parseable", False, _ascii(err))]

    if data is None:  # missing file -> NAME portion vacuous; generic markers still enforced
        denylist, allowlist = [], []
        name_note = "no .cleanroom-thirdparty (NAME denylist vacuous); generic markers enforced"
    else:
        denylist = [str(n) for n in data.get("name_marker_denylist", []) if str(n).strip()]
        allowlist = [str(n) for n in data.get("owner_tool_allowlist", []) if str(n).strip()]
        name_note = "%d denylist name(s) checked" % len(denylist)

    # copyright-sign + denylisted name: part of the NAME family (needs a name to pair with),
    # so it is denylist-driven and vacuous when no file is configured. The copyright sign is
    # harmless in this guard's own source -- no denylisted name follows it here, so the
    # pattern never self-matches.
    cr_res = [(n, re.compile("(?:©|\\(c\\))\\s*" + re.escape(n))) for n in denylist]

    hits = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in (".git", "__pycache__")]
        relroot = os.path.relpath(dp, root).replace("\\", "/")
        if relroot == "tests" or relroot.startswith("tests/"):
            continue  # tests/ fixtures embed denylisted strings on purpose
        for fn in fns:
            if not fn.endswith(TEXT_EXTS):
                continue
            p = os.path.join(dp, fn)
            relp = rel(root, p)
            try:
                raw = read(p)
            except (OSError, UnicodeDecodeError):
                hits.append("%s: unreadable (cannot clear)" % relp)
                continue
            # NAMES: raw scan, span-aware allowlist, NO whole-file exemption (tests/ pruned).
            hits.extend(_name_leaks(relp, raw, denylist, allowlist))
            for name, rx in cr_res:
                if rx.search(raw):
                    hits.append("%s: copyright-sign + denylisted name '%s'" % (relp, name))
            # GENERIC markers / brand / source: fail-closed; exempt only in governance docs.
            hits.extend(_generic_marker_hits(relp, raw))
    hits = sorted(set(hits))
    detail = "; ".join(hits[:25]) if hits else "clean (%s)" % name_note
    return [("C7 cleanroom: no third-party names/markers/source-headers in shipped files",
             not hits, _ascii(detail))]


def check_no_sync_or_lock(root):
    """C9 -- no sync_* prompt-fetcher script anywhere; no *-prompts.lock (positive)."""
    sync_hits, lock_hits = [], []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in (".git", "__pycache__")]
        for fn in fns:
            if re.match(r"sync_.+\.(py|sh|js|ts|mjs|cjs)$", fn) or re.match(r"sync_[A-Za-z0-9_]+$", fn):
                sync_hits.append(rel(root, os.path.join(dp, fn)))
            if fn.endswith("-prompts.lock") or fn == "prompts.lock":
                lock_hits.append(rel(root, os.path.join(dp, fn)))
    return [
        ("C9 sync/lock: no sync_* prompt-fetcher script", not sync_hits,
         ", ".join(sorted(sync_hits)) or "none"),
        ("C9 sync/lock: no *-prompts.lock file (positive or external)", not lock_hits,
         ", ".join(sorted(lock_hits)) or "none"),
    ]


# The clean-room method-note markers a HIGH-RISK PROVENANCE row must carry ((a) wall /
# first-principles / PUBLIC-standard / source-not-open). Shared and per-skill reference
# rows both key off this.
_PROV_NOTE_RE = re.compile(r"\(a\)|not open|first principles|PUBLIC", re.I)


def _prov_row_line(prov, relpath):
    """The PROVENANCE table ROW whose FIRST cell is the backticked path `relpath` (anchored
    at line start as '| `relpath`'), so a mid-sentence prose mention of the same path inside
    some OTHER asset's row (e.g. a `scripts/...py` row that cites a reference in passing) is
    never mistaken for its own row. Returns the row line, or None if there is no such row."""
    pat = re.compile(r"^\s*\|\s*" + re.escape("`%s`" % relpath))
    for ln in prov.splitlines():
        if pat.match(ln):
            return ln
    return None


def _cited_references(root):
    """Every references/**/*.md path CITED inside any SKILL.md, extracted exactly the way
    C1/check_skill_ref_resolve extracts them (so the two checks agree on the cited set)."""
    cited = set()
    for sf in skill_files(root):
        for m in re.findall(r"references[\\/][A-Za-z0-9_./\\-]+\.md", read(sf)):
            cited.add(m.replace("\\", "/"))
    return sorted(cited)


def check_prov_classes(root):
    """C8 -- per-class PROVENANCE coverage + method notes for high-risk classes.

    Reference coverage is TWO-PRONGED: (1) every references/shared/*.md has a row (shared
    knowledge), and (2) EVERY references/**/*.md CITED by a SKILL.md -- including per-skill
    references/<skill>/*.md -- is treated as a HIGH-RISK class and must carry a backtick-
    delimited PROVENANCE row AND a clean-room method note. Without prong (2) a per-skill
    reference a SKILL.md points at could ship with no provenance record at all."""
    prov = read(os.path.join(root, "references", "PROVENANCE.md"))
    headings = "\n".join(ln for ln in prov.splitlines() if ln.lstrip().startswith("## "))
    out = []

    missing_sections = [c for c in PROV_ASSET_CLASSES if c not in headings]
    out.append(("C8 prov: every per-class asset section exists in PROVENANCE",
                not missing_sections,
                "missing: " + ", ".join(missing_sections) if missing_sections
                else "all %d asset classes have a section" % len(PROV_ASSET_CLASSES)))

    shared = sorted(glob.glob(os.path.join(root, "references", "shared", "*.md")))
    missing_rows = [rel(root, s) for s in shared if rel(root, s) not in prov]
    out.append(("C8 prov: every references/shared/*.md has a PROVENANCE row",
                not missing_rows,
                "missing: " + ", ".join(missing_rows) if missing_rows
                else "all %d shared references recorded" % len(shared)))

    out.append(("C8 prov: AGENTS.md has a PROVENANCE row",
                "AGENTS.md" in prov, "AGENTS.md"))

    weak = []
    for s in shared:
        relp = rel(root, s)
        rowline = next((ln for ln in prov.splitlines() if relp in ln), "")
        if rowline and not _PROV_NOTE_RE.search(rowline):
            weak.append(relp)
    out.append(("C8 prov: high-risk reference rows carry a clean-room method note",
                not weak, "weak: " + ", ".join(weak) if weak else "method notes present"))

    # Prong (2): every SKILL-cited per-skill reference must have a real PROVENANCE row
    # (first-cell-anchored, so a passing prose mention does not satisfy it) AND a method note.
    cited = _cited_references(root)
    cite_missing, cite_weak = [], []
    for ref in cited:
        rowline = _prov_row_line(prov, ref)
        if rowline is None:
            cite_missing.append(ref)
        elif not _PROV_NOTE_RE.search(rowline):
            cite_weak.append(ref)
    out.append(("C8 prov: every SKILL-cited per-skill reference has a PROVENANCE row",
                not cite_missing,
                "missing: " + ", ".join(cite_missing) if cite_missing
                else "all %d SKILL-cited references recorded" % len(cited)))
    out.append(("C8 prov: every SKILL-cited per-skill reference carries a clean-room method note",
                not cite_weak,
                "weak: " + ", ".join(cite_weak) if cite_weak
                else "method notes present on all cited references"))
    return out


def check_skill_ref_resolve(root):
    """C1 -- every references/*.md path cited inside a SKILL.md resolves on disk."""
    missing = []
    for sf in skill_files(root):
        txt = read(sf)
        for m in re.findall(r"references[\\/][A-Za-z0-9_./\\-]+\.md", txt):
            norm = m.replace("\\", "/")
            if not os.path.exists(os.path.join(root, *norm.split("/"))):
                missing.append("%s -> %s" % (rel(root, sf), norm))
    return [("C1 skillrefs: references/*.md cited in a SKILL.md resolve on disk",
             not missing, "; ".join(sorted(set(missing))) or "all cited references resolve")]


_DEP_ENTRY_RE = re.compile(r"^\s*[-*]\s+`([^`]+)`")


def _dep_entries(section):
    """The REAL dependency ENTRIES in a section body: a backticked id that is the LEADING
    token of a markdown bullet (`- `<id>` ...`, optionally followed by an em-dash / colon /
    parenthesis / reason). A backticked token embedded MID-SENTENCE inside a bullet (e.g.
    `- not a dependency on `seo-page``) is prose, NOT an entry -- so a severed handoff that
    leaves a lingering prose reference reads as severed, and a disclaimer like
    'not a dependency on `x`' cannot falsely satisfy an edge. The real ## Dependencies bodies
    (qa-gate, design-research, ...) lead each entry with the backticked id, so they still
    parse; non-entry bullets that open with prose (e.g. design-research's
    `- Built-in (Tier 2): WebFetch; ...; `html-extract``) are correctly ignored."""
    entries = set()
    for ln in section.splitlines():
        m = _DEP_ENTRY_RE.match(ln)
        if m:
            entries.add(m.group(1).strip())
    return entries


def check_handoffs(root):
    """C-HANDOFF -- the three named handoffs hold against the CURRENT tree. Dependency edges
    are tested against the REAL backticked bullet ENTRIES of the ## Dependencies section (not
    a raw substring, which a prose mention or a 'not a dependency' disclaimer could fool).
    The Notes-level mutual reference is intentionally a loose prose mention."""
    def deps(skill):
        p = os.path.join(root, "skills", skill, "SKILL.md")
        return _dep_entries(_section(read(p), "Dependencies")) if os.path.exists(p) else set()

    def notes_text(skill):
        p = os.path.join(root, "skills", skill, "SKILL.md")
        return _section(read(p), "Notes") if os.path.exists(p) else ""

    out = []
    out.append(("C-HANDOFF: qa-gate -> seo-page stays an orchestrator Dependency",
                "seo-page" in deps("qa-gate"),
                "seo-page in qa-gate ## Dependencies entries"))
    out.append(("C-HANDOFF: design-research -> seo-cluster stays an orchestrator Dependency",
                "seo-cluster" in deps("design-research"),
                "seo-cluster in design-research ## Dependencies entries"))

    d1 = "design-visual-qa" in deps("seo-drift")
    d2 = "seo-drift" in deps("design-visual-qa")
    out.append(("C-HANDOFF: seo-drift <-> design-visual-qa is NOT a Dependencies edge",
                not (d1 or d2),
                "seo-drift.deps->visual-qa=%s; design-visual-qa.deps->drift=%s" % (d1, d2)))

    n1 = "design-visual-qa" in notes_text("seo-drift")
    n2 = "seo-drift" in notes_text("design-visual-qa")
    out.append(("C-HANDOFF: seo-drift <-> design-visual-qa stay a Notes-level mutual reference",
                n1 and n2,
                "seo-drift.notes->visual-qa=%s; design-visual-qa.notes->drift=%s" % (n1, n2)))
    return out


def check_count_band(root):
    """C-COUNT (record-only this wave) -- enforces when a NEW data/*.csv lands."""
    data, err = _load_thirdparty(root)
    if err:
        return [("C-COUNT: .cleanroom-thirdparty is readable/parseable", False, _ascii(err))]
    if data is None:
        return [("C-COUNT: new data/*.csv row/column independence", True,
                 "no .cleanroom-thirdparty configured (vacuous pass)")]
    counts = data.get("inspiration_counts", [])
    conflicts, checked = [], 0
    for p in sorted(glob.glob(os.path.join(root, "data", "*.csv"))):
        if os.path.basename(p) in GRANDFATHERED_CSVS:
            continue
        checked += 1
        rows, cols = _csv_shape(p)
        c = _count_conflict(rows, cols, counts)
        if c:
            conflicts.append("%s: %s" % (rel(root, p), c))
    detail = ("; ".join(conflicts) if conflicts
              else ("no new CSVs this wave (record-only)" if checked == 0
                    else "%d new CSV(s) clear the +/-2 band and column near-match" % checked))
    return [("C-COUNT: no new data/*.csv within +/-2 row band or column near-match",
             not conflicts, _ascii(detail))]


def check_stdlib_only(root):
    """C11 -- scripts/** import only the stdlib (+ local sibling modules). The stdlib set is
    sys.stdlib_module_names (authoritative on 3.10+), so common roots like email / uuid /
    queue / threading are never false-flagged; a dynamic import with a non-literal argument
    is reported as unverifiable (see _imported_roots)."""
    py_files = glob.glob(os.path.join(root, "scripts", "**", "*.py"), recursive=True)
    local = {os.path.splitext(os.path.basename(p))[0] for p in py_files}
    stdlib = _stdlib_root_names()
    bad = []
    for p in sorted(py_files):
        roots, errs = _imported_roots(p)
        for e in errs:
            bad.append("%s: %s" % (rel(root, p), e))
        for r in sorted(roots):
            if r in stdlib or r in local:
                continue
            bad.append("%s: non-stdlib import '%s'" % (rel(root, p), r))
    return [("C11 stdlib: scripts/** import only the stdlib (+ local siblings)",
             not bad, "; ".join(bad) or "all imports stdlib-only")]


# --- Wave-2 scaffold guards: agents/ layer (C3, C5) + connector Tier-2 (C4) ----------
#
# Additive (MASTER-PLAN 7.4 / Wave-2). All three are pure-Python and never crash the
# gate -- a bug raises and is caught by main()'s per-check try/except as a loud FAIL.
# Output stays ASCII-only (details run through _ascii()).

# The least-privilege primitive set a dispatched leaf may draw its tools from. Anything
# outside it (Task -- the dispatch power -- NotebookEdit, an arbitrary MCP tool, ...) is a
# "clearly-unneeded high-privilege" grant for a leaf and fails C5.
ALLOWED_LEAF_TOOLS = {"read", "glob", "grep", "bash", "write", "webfetch", "websearch"}
# Built-in fetch tools. An agent that fetches via these is "fetch-only" and must NOT also
# hold Bash (if a bundled Bash script does the fetch, the built-in fetch tools are redundant;
# if the built-in tools do it, shell exec is unneeded over-privilege).
FETCH_TOOLS = {"webfetch", "websearch"}
REQUIRED_AGENT_KEYS = ("name", "description", "model", "maxTurns", "tools")
# C3 fenced-block CONTENT (not just heading presence). The ```capability-routing block
# under '## Capability routing' must carry the fixed CAPABILITY-TIERS keys; the
# ```output-contract block under '## Output contract' must be a non-empty machine-parseable
# schema carrying at least these fixed keys. A heading with no fenced block -- or a block
# missing a required key -- is malformed and FAILS C3.
CAPABILITY_ROUTING_KEYS = (
    "capability", "tier1", "tier1_signal", "tier2", "tier2_yields",
    "tier3", "tier3_signal", "tier4", "needs_tier1",
)
# The UNIVERSAL required output-contract keys every dispatched leaf must emit for
# deterministic fan-in (agent/status) and honest tier reporting (tier_ran/needs_tier1/
# tier_line -- which tier ran + the never-fabricate list). Agent-specific keys (target,
# findings, score, dimensions, handoffs, ...) are optional and defined per agent.
OUTPUT_CONTRACT_KEYS = ("agent", "status", "tier_ran", "needs_tier1", "tier_line")
# Orchestrators in this plugin. An agent (a dispatched leaf) must never name one as a
# Dependencies edge (the relationship is a prose cross-reference, never an edge).
ORCHESTRATORS = {
    "seo-audit", "qa-gate", "parallel-build", "design-research", "design-build",
    "blast-prompt", "route-three-brain", "route-codex-review", "route-gemini-context",
}


def _agent_files(root):
    """Real dispatched-leaf agents: agents/*.md minus any '_'-prefixed scaffold
    (e.g. _TEMPLATE.md, which holds angle-bracket placeholders, not a real leaf) and
    the folder's README.md (documentation, not an agent)."""
    return sorted(p for p in glob.glob(os.path.join(root, "agents", "*.md"))
                  if not os.path.basename(p).startswith("_")
                  and os.path.basename(p).lower() != "readme.md")


def _agent_frontmatter(text):
    """Parse leading '--- ... ---' YAML-ish frontmatter into a dict, or None if absent.
    Strips a trailing ' # comment' so a documented value still parses; values may contain
    colons (only the FIRST ':' splits key from value)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        m = re.match(r"\s*([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.*)$", ln)
        if m:
            val = re.sub(r"\s+#.*$", "", m.group(2)).strip()
            fm[m.group(1)] = val
    return fm


def _agent_tools(fm):
    return [t.strip() for t in (fm.get("tools", "") or "").split(",") if t.strip()]


def _has_h2(text, name):
    return re.search(r"(?m)^#{2,}\s+" + re.escape(name) + r"\s*$", text) is not None


def _fenced_blocks(text, info):
    """Inner text of every fenced block opened with exactly ```<info> (closed by ```)."""
    blocks, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        if lines[i].strip() == "```" + info:
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            blocks.append("\n".join(buf))
        i += 1
    return blocks


def _parse_kv(block):
    """key: value pairs from a fenced block body (lowercase snake_case keys)."""
    kv = {}
    for ln in block.splitlines():
        m = re.match(r"\s*([a-z][a-z0-9_]*)\s*:\s*(.*)$", ln)
        if m:
            kv[m.group(1)] = m.group(2).strip()
    return kv


def _capability_routing_kvs(text):
    return [_parse_kv(b) for b in _fenced_blocks(text, "capability-routing")]


def _block_problem(text, heading, info, required_keys):
    """C3 fenced-block CONTENT validation. Returns None if the '## <heading>' section holds
    a fenced ```<info> block carrying every required key (non-empty value); else a reason
    string. A missing heading, a heading with no fenced block, or a block missing a required
    key all FAIL -- so an empty/heading-only section can no longer pass vacuously."""
    if not _has_h2(text, heading):
        return "no ## %s" % heading
    blocks = _fenced_blocks(_section(text, heading), info)
    if not blocks:
        return "## %s has no ```%s fenced block" % (heading, info)
    kv = _parse_kv(blocks[0])
    miss = [k for k in required_keys if not kv.get(k)]
    if miss:
        return "## %s ```%s block missing keys: %s" % (heading, info, ",".join(miss))
    return None


def _example_invokes(extext, basename):
    """C4: True iff the golden-example text contains a runnable COMMAND that invokes
    <basename> -- the script name (optionally quoted) followed by an argument: a flag
    (-x / --x), a redirect/pipe, a positional file path, or a line-continuation that
    carries the args onto the next line. A bare prose mention (`script.py` followed by an
    English word) does NOT match, so merely naming a script no longer counts as exercised."""
    pat = (re.escape(basename) + r"[\"']?[ \t]*"
           r"(?:\\[ \t]*\r?\n[ \t]*)?"
           r"(?:--?\w|[<>|]|\S+\.(?:html|xml|csv|json|txt|md))")
    return re.search(pat, extext) is not None


def _script_token_resolves(root, token):
    """Reuse of the check_refs/_exists resolver, extended to bare basenames. A path-bearing
    token (scripts/seo/x.py) is resolved by os.path.exists like check_refs; a bare basename
    (x.py, as the tier2 field writes it) resolves if it exists anywhere under scripts/."""
    norm = token.replace("\\", "/").lstrip("./")
    if "/" in norm:
        return os.path.exists(os.path.join(root, *norm.split("/")))
    return bool(glob.glob(os.path.join(root, "scripts", "**", norm), recursive=True))


def _concat_dir_text(d):
    """All text-file content under a directory, concatenated (for the golden-example scan)."""
    if not os.path.isdir(d):
        return ""
    parts = []
    for dp, _dns, fns in os.walk(d):
        for fn in fns:
            if fn.endswith(TEXT_EXTS):
                try:
                    parts.append(read(os.path.join(dp, fn)))
                except (OSError, UnicodeDecodeError):
                    pass
    return "\n".join(parts)


def _dispatch_sources(root):
    """Files that may carry a ```dispatch block: every SKILL.md plus any
    references/**/dispatch-matrix.md (per-skill, e.g. references/seo-audit/, or the
    references/ root). Walked so a per-skill dispatch matrix is found wherever it lives."""
    sources = list(skill_files(root))
    refs_root = os.path.join(root, "references")
    for dp, _dn, fns in os.walk(refs_root):
        for fn in fns:
            if fn == "dispatch-matrix.md":
                sources.append(os.path.join(dp, fn))
    return sources


def _dispatch_names(root):
    """Every specialist named in a ```dispatch block (always + conditional), deduped."""
    names = set()
    for sp in _dispatch_sources(root):
        for block in _fenced_blocks(read(sp), "dispatch"):
            kv = _parse_kv(block)
            for key in ("always", "conditional"):
                for n in kv.get(key, "").split(","):
                    n = n.strip()
                    if n:
                        names.add(n)
    return names


def _dispatch_splits(root):
    """Every fenced ```dispatch block in an orchestrator SKILL.md or a
    references/**/dispatch-matrix.md, as (source, always_count, conditional_count).
    The dispatch-shape guard reads these; W4 lands the seo-audit block."""
    out = []
    for sp in _dispatch_sources(root):
        for block in _fenced_blocks(read(sp), "dispatch"):
            kv = _parse_kv(block)
            a = [x for x in kv.get("always", "").split(",") if x.strip()]
            c = [x for x in kv.get("conditional", "").split(",") if x.strip()]
            out.append((rel(root, sp), len(a), len(c)))
    return out


def check_agent_least_privilege(root):
    """C5 -- agent frontmatter completeness + least-privilege tool grants."""
    missing_keys, fetch_bash, overpriv = [], [], []
    for p in _agent_files(root):
        relp, text = rel(root, p), read(p)
        fm = _agent_frontmatter(text)
        if fm is None:
            missing_keys.append("%s: no YAML frontmatter" % relp)
            continue
        miss = [k for k in REQUIRED_AGENT_KEYS if not fm.get(k)]
        if miss:
            missing_keys.append("%s: missing %s" % (relp, ",".join(miss)))
        tools = {t.lower() for t in _agent_tools(fm)}
        if (tools & FETCH_TOOLS) and "bash" in tools:
            fetch_bash.append("%s: holds %s + Bash" % (relp, ",".join(sorted(tools & FETCH_TOOLS))))
        extra = sorted(tools - ALLOWED_LEAF_TOOLS)
        if extra:
            overpriv.append("%s: %s" % (relp, ",".join(extra)))
    return [
        ("C5 agents: every agent has the required frontmatter keys (name/description/model/maxTurns/tools)",
         not missing_keys, _ascii("; ".join(missing_keys) or "all agents declare the required frontmatter keys")),
        ("C5 agents: no fetch-only agent also holds Bash", not fetch_bash,
         _ascii("; ".join(fetch_bash) or "no fetch-tool + Bash over-grant")),
        ("C5 agents: no agent grants a clearly-unneeded high-privilege tool", not overpriv,
         _ascii("; ".join(overpriv) or "all agent tools within the least-privilege leaf set")),
    ]


def check_agent_wellformed(root):
    """C3 -- agent well-formedness (required body blocks), one-directional DAG (no
    orchestrator dependency, no agent->agent call), and the dispatch-shape do-not-match guard."""
    no_routing, no_output, orch_dep, agent_call = [], [], [], []
    for p in _agent_files(root):
        relp, text = rel(root, p), read(p)
        me = os.path.splitext(os.path.basename(p))[0]
        rprob = _block_problem(text, "Capability routing", "capability-routing", CAPABILITY_ROUTING_KEYS)
        if rprob:
            no_routing.append("%s: %s" % (relp, rprob))
        oprob = _block_problem(text, "Output contract", "output-contract", OUTPUT_CONTRACT_KEYS)
        if oprob:
            no_output.append("%s: %s" % (relp, oprob))
        bad = sorted(d for d in _dep_entries(_section(text, "Dependencies")) if d in ORCHESTRATORS)
        if bad:
            orch_dep.append("%s: %s" % (relp, ",".join(bad)))
        tools = {t.lower() for t in _agent_tools(_agent_frontmatter(text) or {})}
        calls = []
        if "task" in tools:
            calls.append("holds Task")
        for other in re.findall(r"agents[\\/]([A-Za-z0-9_-]+)\.md", text):
            if other != me and not other.startswith("_"):
                calls.append("references agents/%s.md" % other)
        if calls:
            agent_call.append("%s: %s" % (relp, "; ".join(sorted(set(calls)))))
    shape_hits = ["%s: 8-always + 7-conditional (mirrors a third-party dispatch split)" % src
                  for src, a, c in _dispatch_splits(root) if a == 8 and c == 7]
    wf_detail = no_routing + no_output  # each entry is already "relp: <reason>"
    return [
        ("C3 agents: every agent has a ## Capability routing + a ## Output contract block",
         not (no_routing or no_output), _ascii("; ".join(wf_detail) or "all agents well-formed")),
        ("C3 agents: no agent names an orchestrator as a Dependencies edge", not orch_dep,
         _ascii("; ".join(orch_dep) or "no agent->orchestrator dependency edge")),
        ("C3 agents: no agent calls another agent (one-directional DAG)", not agent_call,
         _ascii("; ".join(agent_call) or "no agent->agent edge")),
        ("C3 dispatch-shape: no orchestrator dispatch mirrors an 8-always + 7-conditional split",
         not shape_hits, _ascii("; ".join(shape_hits) or "no 8+7 dispatch split (dispatch shape derived from our own specialists, not mirrored)")),
    ]


def check_agent_parity(root):
    """C3 parity -- name<->file<->sibling-skill. For every real agents/<name>.md (the
    _-prefixed template is excluded), the frontmatter `name` must equal the filename stem
    AND a sibling skills/<name>/SKILL.md (the skill the agent wraps) must exist. A
    well-formed ORPHAN agent (no sibling skill) or a name!=filename mismatch FAILS.
    (Orchestrator dispatch==disk parity is deferred to W4 -- this is file/name/sibling only.)"""
    name_mismatch, orphan = [], []
    for p in _agent_files(root):
        relp = rel(root, p)
        stem = os.path.splitext(os.path.basename(p))[0]
        fm = _agent_frontmatter(read(p)) or {}
        nm = (fm.get("name", "") or "").strip()
        if nm != stem:
            name_mismatch.append("%s: frontmatter name=%r != filename %r" % (relp, nm, stem))
        if not os.path.exists(os.path.join(root, "skills", stem, "SKILL.md")):
            orphan.append("%s: no sibling skills/%s/SKILL.md (orphan agent)" % (relp, stem))
    return [
        ("C3 agents: every agent's frontmatter name matches its filename", not name_mismatch,
         _ascii("; ".join(name_mismatch) or "all agent names match their filenames")),
        ("C3 agents: every agent wraps an existing sibling skill (skills/<name>/SKILL.md)", not orphan,
         _ascii("; ".join(orphan) or "all agents wrap an existing sibling skill")),
    ]


def check_dispatch_parity(root):
    """C3 dispatch==disk parity (W4). Two directions:
      dispatch -> disk: every specialist named in a ```dispatch block has an
                        agents/<name>.md on disk (an orchestrator can't claim a
                        specialist with no agent).
      disk -> used:     every non-template agent on disk is wired into an orchestrator
                        -- named in a ```dispatch block OR referenced in an orchestrator
                        SKILL.md body (prose dispatch, e.g. qa-gate phase 3 ->
                        design-accessibility). Many orchestrators -> one leaf is legal.
    (The W2 file/name/sibling parity in check_agent_parity still holds; this adds the
    dispatch-list reconciliation that was deferred to W4.)"""
    dispatched = _dispatch_names(root)
    agents = {os.path.splitext(os.path.basename(p))[0] for p in _agent_files(root)}
    orch_text = ""
    for sf in skill_files(root):
        if os.path.basename(os.path.dirname(sf)) in ORCHESTRATORS:
            orch_text += "\n" + read(sf)
    referenced = {a for a in agents if re.search(r"\b%s\b" % re.escape(a), orch_text)}
    used = dispatched | referenced
    missing_agent = sorted(n for n in dispatched if n not in agents)
    unused_agent = sorted(a for a in agents if a not in used)
    return [
        ("C3 dispatch-parity: every dispatched specialist has an agent on disk", not missing_agent,
         _ascii("; ".join("%s: named in a dispatch block but no agents/%s.md" % (n, n) for n in missing_agent)
                or "every dispatched specialist resolves to an agent on disk")),
        ("C3 dispatch-parity: every agent is dispatched by an orchestrator (dispatch block or prose)", not unused_agent,
         _ascii("; ".join("%s: on disk but no orchestrator dispatches it" % a for a in unused_agent)
                or "every agent is wired into an orchestrator")),
    ]


def check_tier2_present(root):
    """C4 -- every skill with a machine-parseable ```capability-routing block ships a
    non-empty Tier-2 whose named script resolves on disk and is exercised by a golden example."""
    empty, noscript, noexample = [], [], []
    for sf in skill_files(root):
        name = os.path.basename(os.path.dirname(sf))
        for kv in _capability_routing_kvs(read(sf)):
            if str(kv.get("c4_exempt", "")).strip().lower() == "true" or name == "seo-image-gen":
                continue  # exempt-by-spec (image-pixel generation has no free substitute)
            tier2 = (kv.get("tier2", "") or "").strip()
            if not tier2 or tier2.lower() in ("none", "-", "--", "n/a"):
                empty.append("%s: tier2=%r" % (name, tier2))
                continue
            scripts = re.findall(r"[A-Za-z0-9_][A-Za-z0-9_./\\-]*\.py\b", tier2)
            resolved = [s for s in scripts if _script_token_resolves(root, s)]
            if not resolved:
                noscript.append("%s: tier2 names no on-disk script (%s)" % (name, ",".join(scripts) or "none"))
                continue
            extext = _concat_dir_text(os.path.join(root, "references", "examples", name))
            # Strict: EVERY resolved Tier-2 script must be invoked by a runnable command in
            # the golden -- a bare basename mention no longer counts as exercised.
            not_invoked = sorted({os.path.basename(s) for s in resolved
                                  if not _example_invokes(extext, os.path.basename(s))})
            if not_invoked:
                noexample.append("%s: golden example names but does not invoke %s (no runnable command)"
                                 % (name, ",".join(not_invoked)))
    return [
        ("C4 tier2: every routing-block skill declares a non-empty Tier-2", not empty,
         _ascii("; ".join(empty) or "all routing-block skills declare a Tier-2")),
        ("C4 tier2: every Tier-2 names a script that resolves on disk", not noscript,
         _ascii("; ".join(noscript) or "all Tier-2 scripts resolve on disk")),
        ("C4 tier2: every routing-block skill has a golden example exercising its Tier-2", not noexample,
         _ascii("; ".join(noexample) or "all Tier-2 paths exercised by a golden example")),
    ]


def _frontmatter_block(text):
    m = re.match(r"(?s)^\s*---\n(.*?)\n---", text)
    return m.group(1) if m else ""


def _quoted_phrases(text):
    """Every "double-quoted" phrase (>=3 chars) in a string, lowercased -- the trigger
    phrases a skill claims."""
    return [m.group(1).strip().lower() for m in re.finditer(r'"([^"]{3,}?)"', text or "")]


def check_duplicate_triggers(root):
    """C2 -- no trigger phrase is claimed by two different skills (a collision routes the
    user's intent ambiguously). Scans each skill's frontmatter (description) + ## Triggers
    for quoted phrases; a phrase owned by >=2 skills FAILS, so a NEW duplicate trigger
    cannot ship without a disambiguator."""
    phrase_to = {}
    for sf in skill_files(root):
        name = os.path.basename(os.path.dirname(sf))
        text = read(sf)
        phrases = set(_quoted_phrases(_frontmatter_block(text))) | set(
            _quoted_phrases(_section(text, "Triggers")))
        for ph in phrases:
            phrase_to.setdefault(ph, set()).add(name)
    dupes = {ph: sorted(v) for ph, v in phrase_to.items() if len(v) > 1}
    return [(
        "C2 triggers: no trigger phrase is claimed by two skills",
        not dupes,
        _ascii("; ".join("%r shared by %s" % (ph, "/".join(sk)) for ph, sk in sorted(dupes.items()))
               or "no duplicate trigger phrase across skills"),
    )]


def _depth_tiers(root):
    """Parse the ```depth-tiers block in SHIPPING.md -> {core:[...], lite:[...], routing:[...]}."""
    sp = os.path.join(root, "SHIPPING.md")
    if not os.path.exists(sp):
        return {}
    for block in _fenced_blocks(read(sp), "depth-tiers"):
        kv = _parse_kv(block)
        return {k: [x.strip() for x in kv.get(k, "").split(",") if x.strip()]
                for k in ("core", "lite", "routing")}
    return {}


def check_status_truth(root):
    """C10 -- the Core/Lite/routing depth tiers PARTITION the real skills/ folders on disk
    exactly (no skill missing, none invented, none double-counted), and the stated
    breakdown triangulates across SHIPPING / README / plugin.json. This makes the
    '45 Stable (N Core / M Lite / K routing)' claim mechanically un-fakeable."""
    disk = {os.path.basename(os.path.dirname(p)) for p in skill_files(root)}
    part = _depth_tiers(root)
    core, lite, routing = part.get("core", []), part.get("lite", []), part.get("routing", [])
    listed = core + lite + routing
    listed_set = set(listed)
    problems = []
    dupes = sorted(x for x in listed_set if listed.count(x) > 1)
    if dupes:
        problems.append("skill in >1 tier: " + ",".join(dupes))
    missing = sorted(disk - listed_set)
    if missing:
        problems.append("on disk but in no tier: " + ",".join(missing))
    extra = sorted(listed_set - disk)
    if extra:
        problems.append("tier names a non-existent skill: " + ",".join(extra))
    routing_disk = sorted(s for s in disk if s.startswith("route-"))
    if sorted(routing) != routing_disk:
        problems.append("routing tier %s != route-* on disk %s" % (sorted(routing), routing_disk))
    n, m, k, tot = len(core), len(lite), len(routing), len(disk)
    rows = [(
        "C10 status-truth: Core/Lite/routing tiers partition the skills on disk exactly",
        not problems,
        _ascii("; ".join(problems) or
               "%d Core + %d Lite + %d routing = %d skills, exact partition" % (n, m, k, tot)),
    )]
    # triangulate the stated breakdown across the docs
    ship = read(os.path.join(root, "SHIPPING.md"))
    readme = read(os.path.join(root, "README.md"))
    pj = read(os.path.join(root, ".claude-plugin", "plugin.json"))

    def _states(text):
        return bool(re.search(r"\b%d\b\s*[Cc]ore" % n, text)
                    and re.search(r"\b%d\b\s*[Ll]ite" % m, text)
                    and re.search(r"\b%d\b\s*[Rr]outing" % k, text)
                    and re.search(r"\b%d\b" % tot, text))
    tri = [d for d, t in (("SHIPPING.md", ship), ("README.md", readme),
                          ("plugin.json", pj)) if not _states(t)]
    rows.append((
        "C10 status-truth: the Core/Lite/routing breakdown triangulates across SHIPPING/README/plugin.json",
        not tri,
        _ascii("breakdown missing/mismatched in: " + ",".join(tri) if tri else
               "%d Core / %d Lite / %d routing / %d total stated consistently" % (n, m, k, tot)),
    ))
    return rows


CHECKS = [
    ("smoke", check_smoke),
    ("refs", check_refs),
    ("prov", check_prov),
    ("clean", check_clean),
    ("config", check_config),
    ("counts", check_counts),
    ("version", check_version),
    ("paths", check_paths),
    ("market", check_market),
    # Wave-0 clean-room / governance guards (additive; MASTER-PLAN 7.3/7.4):
    ("c7_cleanroom", check_cleanroom_thirdparty),
    ("c9_sync_lock", check_no_sync_or_lock),
    ("c8_prov_classes", check_prov_classes),
    ("c1_skill_refs", check_skill_ref_resolve),
    ("c_handoff", check_handoffs),
    ("c_count", check_count_band),
    ("c11_stdlib", check_stdlib_only),
    # Wave-2 scaffold guards (agents/ layer + connector Tier-2; additive, MASTER-PLAN 7.4):
    ("c5_agent_priv", check_agent_least_privilege),
    ("c3_agent_wellformed", check_agent_wellformed),
    ("c3_agent_parity", check_agent_parity),
    # Wave-4 orchestrator wiring: dispatch-list <-> agents-on-disk reconciliation.
    ("c3_dispatch_parity", check_dispatch_parity),
    ("c4_tier2", check_tier2_present),
    # Wave-5 status-truth + release certification.
    ("c2_triggers", check_duplicate_triggers),
    ("c10_status_truth", check_status_truth),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Release gate for the plugin.")
    ap.add_argument("--root", default=None, help="plugin root to check (default: this repo)")
    ap.add_argument("--skip-smoke", action="store_true", help="skip the smoke_test subprocess")
    args = ap.parse_args(argv)
    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    results = []
    for key, fn in CHECKS:
        try:
            if key == "smoke":
                results.extend(fn(root, skip_smoke=args.skip_smoke))
            else:
                results.extend(fn(root))
        except Exception as e:  # a check bug must fail loudly, not crash the gate
            results.append(("%s check ran" % key, False, "ERROR: %s" % e))

    for name, ok, detail in results:
        print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, (" -- " + detail) if detail else ""))

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("\n%d/%d checks passed." % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
