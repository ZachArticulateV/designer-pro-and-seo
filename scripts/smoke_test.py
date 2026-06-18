#!/usr/bin/env python3
"""
smoke_test.py — Install verification for the shipping (v0.4.x) skill set.

Run after install to confirm the engine, data libraries, and porter work on your
machine. Exits 0 if all checks pass, 1 otherwise. Standard library only.

Usage:
  python3 scripts/smoke_test.py        # from the plugin root (or anywhere)
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def py():
    """Return an invocable Python command (this interpreter)."""
    return [sys.executable]


def main():
    # 1. Required data libraries present
    required = ["ui-styles.csv", "color-palettes.csv", "font-pairings.csv",
                "ux-rules.csv", "product-types.csv"]
    missing = [f for f in required if not os.path.exists(os.path.join(DATA, f))]
    if "color-palettes.csv" in missing:
        # try to generate it (it's produced, not hand-authored)
        subprocess.run(py() + [os.path.join(ROOT, "scripts", "design", "gen_palettes.py")],
                       capture_output=True)
        missing = [f for f in required if not os.path.exists(os.path.join(DATA, f))]
    check("data libraries present", not missing,
          "missing: " + ", ".join(missing) if missing else "all 5 present")

    # 2. Palette generator runs
    r = subprocess.run(py() + [os.path.join(ROOT, "scripts", "design", "gen_palettes.py"), "--print"],
                       capture_output=True, encoding="utf-8")
    check("gen_palettes.py runs", r.returncode == 0 and "primary" in r.stdout,
          r.stderr.strip()[:120])

    # 3. design_system.py returns valid JSON with required keys
    r = subprocess.run(py() + [os.path.join(ROOT, "scripts", "design", "design_system.py"),
                               "--product-type", "saas-landing", "--industry", "saas",
                               "--keywords", "modern, minimal"],
                       capture_output=True, encoding="utf-8")
    ok = r.returncode == 0
    keys_ok = False
    if ok:
        try:
            d = json.loads(r.stdout)
            keys_ok = all(k in d for k in ("pattern", "style", "palette", "typography",
                                           "effects", "pre_delivery_checklist"))
        except json.JSONDecodeError:
            keys_ok = False
    check("design_system.py composes a system", ok and keys_ok,
          "valid JSON with all dimensions" if keys_ok else r.stderr.strip()[:120])

    # 4. design engine tolerates a missing data dir (graceful fallback)
    with tempfile.TemporaryDirectory() as empty:
        r = subprocess.run(py() + [os.path.join(ROOT, "scripts", "design", "design_system.py"),
                                   "--product-type", "x", "--industry", "y",
                                   "--keywords", "z", "--data-dir", empty],
                           capture_output=True, encoding="utf-8")
        grace = r.returncode == 0 and '"_fallbacks"' in r.stdout
    check("design engine degrades gracefully (no data)", grace,
          "fell back without crashing")

    # 5. portable_html.py inlines the bundled fixture
    fixture = os.path.join(ROOT, "references", "examples", "portable-html", "src", "index.html")
    if os.path.exists(fixture):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "portable.html")
            r = subprocess.run(py() + [os.path.join(ROOT, "scripts", "workflow", "portable_html.py"),
                                       "--in", fixture, "--out", out, "--target", "generic"],
                               capture_output=True, encoding="utf-8")
            ok = r.returncode == 0 and os.path.exists(out)
            selfcontained = False
            if ok:
                html = open(out, encoding="utf-8").read()
                selfcontained = ("<style>" in html
                                 and 'src="app.js"' not in html
                                 and "sourceMappingURL" not in html)
            check("portable_html.py inlines fixture", ok and selfcontained,
                  "self-contained output" if selfcontained else r.stderr.strip()[:120])
    else:
        check("portable_html.py inlines fixture", False, "fixture missing")

    # 6. csv_to_report.py profiles a CSV and redacts sensitive columns
    with tempfile.TemporaryDirectory() as td:
        cpath = os.path.join(td, "t.csv")
        with open(cpath, "w", encoding="utf-8") as f:
            f.write("name,password,hours\nA,secret1,40\nB,secret2,12\n")
        r = subprocess.run(py() + [os.path.join(ROOT, "scripts", "workflow", "csv_to_report.py"),
                                   "--in", cpath], capture_output=True, encoding="utf-8")
        ok = r.returncode == 0 and '"row_count": 2' in r.stdout
        redacted = ok and "secret1" not in r.stdout and "[redacted]" in r.stdout
        check("csv_to_report.py profiles + redacts secrets", redacted,
              "2 rows, password redacted" if redacted else r.stderr.strip()[:120])

    # 7. Batch A–E scripts: each runs and produces expected output
    def runs(rel, args, needle):
        r = subprocess.run(py() + [os.path.join(ROOT, *rel.split("/"))] + args,
                           capture_output=True, encoding="utf-8")
        ok = r.returncode == 0 and needle in r.stdout
        check(f"{rel} runs", ok, "ok" if ok else (r.stderr.strip()[:120] or "needle not found"))
        return r

    runs("scripts/seo/schema_gen.py", ["--type", "Article",
         "--data", '{"headline":"H","author":"A","datePublished":"2026-01-01"}'], '"ok": true')
    runs("scripts/seo/hreflang_tools.py", ["--validate",
         '[{"hreflang":"en-us","href":"https://s.com/"}]', "--self", "https://s.com/"], '"action": "validate"')
    fixture = os.path.join(ROOT, "references", "examples", "portable-html", "src", "index.html")
    runs("scripts/seo/tech_audit.py", ["--file", fixture, "--no-network"], '"findings"')
    with tempfile.TemporaryDirectory() as td:
        # geo_check on a tiny content file
        cp = os.path.join(td, "c.md")
        open(cp, "w", encoding="utf-8").write("In 2026, INP under 200ms is required, and 43% of sites fail it.\n")
        runs("scripts/seo/geo_check.py", ["--content", cp, "--no-network"], '"citability"')
        # sitemap generate then validate
        up = os.path.join(td, "u.txt"); open(up, "w").write("https://s.com/\n")
        sm = os.path.join(td, "sm.xml")
        runs("scripts/seo/sitemap_tools.py", ["--generate", "--urls", up, "--out", sm], '"generate"')
        runs("scripts/seo/sitemap_tools.py", ["--validate", sm], '"valid": true')
        # drift capture
        base = os.path.join(td, "b.json")
        runs("scripts/seo/drift_tools.py", ["--capture", "--file", fixture, "--out", base], '"capture"')
        # render_page then tokens_emit from its engine
        page = os.path.join(td, "p.html")
        runs("scripts/design/render_page.py", ["--product-type", "saas-landing",
             "--industry", "saas", "--keywords", "modern", "--out", page], '"out"')
        sc = subprocess.run(py() + [os.path.join(ROOT, "scripts", "design", "design_system.py"),
             "--product-type", "saas-landing", "--industry", "saas", "--keywords", "modern"],
             capture_output=True, encoding="utf-8")
        dj = os.path.join(td, "ds.json"); open(dj, "w", encoding="utf-8").write(sc.stdout)
        runs("scripts/design/tokens_emit.py", ["--design-json", dj, "--format", "css", "--print"], "--color-primary")

        # deeper sub-command coverage (U10)
        runs("scripts/seo/schema_gen.py", ["--validate",
             '{"@context":"https://schema.org","@type":"Article","headline":"H","author":"A","datePublished":"2026-01-01"}'],
             '"ok": true')
        rbad = subprocess.run(py() + [os.path.join(ROOT, "scripts", "seo", "schema_gen.py"),
               "--validate", '{"@context":"https://schema.org","@type":"Article","headline":"H"}'],
               capture_output=True, encoding="utf-8")
        check("schema_gen.py flags invalid schema (missing required)",
              rbad.returncode == 0 and '"ok": false' in rbad.stdout,
              "flagged" if '"ok": false' in rbad.stdout else "did not flag")
        runs("scripts/seo/schema_gen.py", ["--list"], "LocalBusiness")
        runs("scripts/seo/hreflang_tools.py", ["--generate", "--map",
             '{"en-us":"https://s.com/","fr-fr":"https://s.com/fr/"}', "--x-default", "https://s.com/"],
             "hreflang")
        runs("scripts/seo/drift_tools.py", ["--diff", "--file", fixture, "--baseline", base], '"diff"')
        gcsv = os.path.join(td, "g.csv")
        open(gcsv, "w", encoding="utf-8").write("team,role,hours\nA,dev,40\nA,qa,10\nB,dev,20\n")
        runs("scripts/workflow/csv_to_report.py", ["--in", gcsv, "--group-by", "team"], '"group_by"')
        runs("scripts/workflow/csv_to_report.py", ["--in", gcsv, "--filter", "team=A"], '"row_count": 2')
        runs("scripts/workflow/csv_to_report.py", ["--in", gcsv, "--select", "team,hours"], '"columns"')
        for tgt in ["wordpress", "ghl", "webflow", "wix", "framer", "squarespace", "carrd"]:
            op = os.path.join(td, "p-%s.html" % tgt)
            rt = subprocess.run(py() + [os.path.join(ROOT, "scripts", "workflow", "portable_html.py"),
                 "--in", fixture, "--out", op, "--target", tgt], capture_output=True, encoding="utf-8")
            html_t = (open(op, encoding="utf-8").read()
                      if (rt.returncode == 0 and os.path.exists(op)) else "")
            ok = ("<style>" in html_t and 'src="app.js"' not in html_t
                  and "sourceMappingURL" not in html_t)
            check("portable_html.py target %s" % tgt, ok,
                  "self-contained" if ok else (rt.stderr.strip()[:80] or "not self-contained"))

    # capability_probe: reports available CLIs/env as JSON (always exits 0)
    runs("scripts/workflow/capability_probe.py", [], '"cli"')

    # golden oracle: design_system --human matches the committed fixture (U10)
    golden = os.path.join(ROOT, "references", "examples", "design-system", "saas-landing.txt")
    rg = subprocess.run(py() + [os.path.join(ROOT, "scripts", "design", "design_system.py"),
         "--product-type", "saas-landing", "--industry", "saas",
         "--keywords", "modern, trustworthy, minimal", "--human"],
         capture_output=True, encoding="utf-8")
    got = (rg.stdout or "").replace("\r\n", "\n")
    want = open(golden, encoding="utf-8").read().replace("\r\n", "\n") if os.path.exists(golden) else None
    ok = rg.returncode == 0 and want is not None and got == want
    check("design_system --human matches golden fixture", ok,
          "exact match (newlines normalized)" if ok else "drift vs saas-landing.txt (regenerate if intended)")

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} checks passed.")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
