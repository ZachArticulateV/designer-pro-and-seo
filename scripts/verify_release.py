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

Usage:
  python3 scripts/verify_release.py            # from anywhere
  python3 scripts/verify_release.py --root DIR # check a copy (used by self-tests)
  python3 scripts/verify_release.py --skip-smoke
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

TEXT_EXTS = (".md", ".py", ".json", ".csv", ".txt", ".html", ".css", ".js")


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
