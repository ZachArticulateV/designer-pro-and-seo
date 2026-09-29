"""v1.9 depth: qa_gate.py (the static 9-phase gate runner), cro_audit.py (design-cro) and
motion_audit.py (design-motion).

Offline, stdlib-only; runs under unittest and pytest.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "references", "examples")
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "design"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "seo"))
import cro_audit  # noqa: E402
import motion_audit  # noqa: E402
import qa_gate  # noqa: E402

GATE = os.path.join(ROOT, "scripts", "workflow", "qa_gate.py")


def run_gate(*args):
    r = subprocess.run([sys.executable, GATE, *args], capture_output=True, encoding="utf-8")
    return r.returncode, r.stdout


class QaGateTest(unittest.TestCase):
    def test_golden_build_fails_with_critical_risk(self):
        rc, out = run_gate("--dir", os.path.join(EX, "qa-gate", "build"), "--base-url",
                           "https://example.test")
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertEqual((d["status"], d["risk"], d["client_ready"]), ("FAIL", "Critical", "NO"))
        crit = " | ".join(i["finding"] for i in d["items"] if i["severity"] == "critical")
        self.assertIn("AWS access key", crit)
        self.assertIn("robots.txt blocks Googlebot", crit)
        self.assertIn("placeholder", crit.lower())
        self.assertEqual(sum(1 for i in d["items"] if "lorem" in i["finding"].lower()), 1)
        self.assertEqual(d["phases"]["5"], "FAIL")
        self.assertEqual(d["phases"]["9"], "FAIL")
        self.assertTrue(d["phases"]["2"].startswith("N/A"))

    def test_clean_enough_site_is_conditional(self):
        rc, out = run_gate("--dir", os.path.join(EX, "seo-sitemap", "site"), "--base-url",
                           "https://example.test")
        d = json.loads(out)
        self.assertEqual(d["status"], "CONDITIONAL PASS")
        self.assertEqual(d["client_ready"], "YES")
        broken = [i for i in d["items"] if i["finding"].startswith("broken internal link")]
        self.assertEqual(len(broken), 1)

    def test_file_mode_marks_site_phases_na_and_flags_http(self):
        rc, out = run_gate("--file", os.path.join(EX, "seo-technical", "sample-page.html"),
                           "--url", "http://example.test/benches")
        d = json.loads(out)
        self.assertTrue(d["phases"]["9"].startswith("N/A"))
        self.assertIn("Not served over HTTPS",
                      [i["finding"] for i in d["items"] if i["severity"] == "critical"])

    def test_report_renders_template_with_fixed_date(self):
        rc, out = run_gate("--dir", os.path.join(EX, "qa-gate", "build"), "--base-url",
                           "https://example.test", "--report", "--as-of", "2026-09-25",
                           "--project", "Cedar Bench Co.")
        self.assertIn("OVERALL STATUS: FAIL", out)
        self.assertIn("Date:       2026-09-25", out)
        self.assertNotIn("{{", out)

    def test_secret_patterns(self):
        g = qa_gate.Gate()
        g.page_checks('<html><body><h1>x</h1><script>k="sk_live_%s"</script></body></html>'
                      % ("a" * 24), "https://e.test/", "p")
        self.assertTrue(any("Stripe" in i["finding"] for i in g.items.values()))

    def test_bad_input(self):
        self.assertEqual(run_gate("--dir", "/nope", "--base-url", "https://e.test")[0], 1)


class CroTest(unittest.TestCase):
    def test_golden_landing(self):
        html = open(os.path.join(EX, "design-cro", "landing.html"), encoding="utf-8").read()
        r = cro_audit.audit(html)
        self.assertEqual([f["code"] for f in r["findings"]],
                         ["K10", "K3", "K4", "K6", "K9", "K11", "K5"])
        self.assertEqual(r["score"], 60)
        self.assertEqual(r["findings"][0]["rule"]["rule"], "Page reflects intent in first 3 seconds")

    def test_strong_page_is_clean(self):
        html = ("<html><body><main><h1>Custom cedar benches built to fit your patio</h1>"
                "<p>Handmade in two weeks, delivered free across the metro area.</p>"
                '<a class="btn" href="/quote">Get my free quote</a>'
                "<p>Rated 4.9 from 212 verified customer reviews.</p>"
                '<form action="/q"><input name="n" aria-label="Name"><input type="email" '
                'aria-label="Email"><button>Get my quote</button></form>'
                '<p>Call <a href="tel:+15552014477">555-201-4477</a></p></main></body></html>')
        r = cro_audit.audit(html)
        self.assertEqual(r["findings"], [])
        self.assertEqual(r["score"], 100)

    def test_no_cta_no_trust_no_contact(self):
        r = cro_audit.audit("<html><body><h1>Benches</h1><p>We make benches.</p></body></html>")
        self.assertTrue({"K1", "K7", "K9"} <= {f["code"] for f in r["findings"]})


class MotionTest(unittest.TestCase):
    def test_golden(self):
        css = open(os.path.join(EX, "design-motion", "styles.css"), encoding="utf-8").read()
        html = open(os.path.join(EX, "design-motion", "page.html"), encoding="utf-8").read()
        r = motion_audit.audit(css, html)
        self.assertEqual([f["code"] for f in r["findings"]],
                         ["M1", "M8", "M2", "M3", "M4", "M5", "M6", "M7"])
        self.assertEqual(r["score"], 60)

    def test_reduced_motion_guard_clears_m1_m5_m7(self):
        css = (".b{animation:spin 2s linear infinite} html{scroll-behavior:smooth}"
               "@media (prefers-reduced-motion: reduce){*,*::before{animation-duration:.01ms"
               " !important;transition-duration:.01ms !important;scroll-behavior:auto !important}}")
        codes = {f["code"] for f in motion_audit.audit(css)["findings"]}
        self.assertFalse({"M1", "M5", "M7"} & codes)

    def test_focus_visible_replacement(self):
        css = ".b:focus{outline:none}.b:focus-visible{outline:2px solid #1a4}"
        self.assertNotIn("M8", {f["code"] for f in motion_audit.audit(css)["findings"]})
        self.assertIn("M8", {f["code"] for f in motion_audit.audit(".b:focus{outline:0}")["findings"]})

    def test_cli(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.css")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(".a{transition:opacity 200ms}")
            r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "design", "motion_audit.py"),
                                "--css", p], capture_output=True, encoding="utf-8")
            self.assertIn("M1", {f["code"] for f in json.loads(r.stdout)["findings"]})
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "design", "motion_audit.py")],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
