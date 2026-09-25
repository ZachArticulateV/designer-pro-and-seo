"""v1.4 AI-visibility depth: llms_txt.py (generate/validate), geo_check fan-out coverage +
llms.txt structure scoring, and the seo-drift D15 AI-crawler-verdict rule.

Offline, stdlib-only; runs under unittest and pytest.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEO = os.path.join(ROOT, "scripts", "seo")
sys.path.insert(0, SEO)
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
import drift_severity  # noqa: E402
import drift_tools  # noqa: E402
import geo_check  # noqa: E402
import llms_txt  # noqa: E402

GOOD = """# Cedar Bench Co.

> Handmade cedar outdoor benches, shipped flat-packed across the US.

We build every bench from kiln-dried western red cedar.

## Products

- [Classic Bench](https://example.test/benches/classic): our best seller
- [Porch Swing](https://example.test/benches/porch-swing)

## Optional

- [Care guide](https://example.test/guides/care)
"""


def sev(v, s, needle):
    return any(i["severity"] == s and needle in i["finding"] for i in v["issues"])


class LlmsValidateTest(unittest.TestCase):
    def test_good_file_is_valid_100(self):
        v = llms_txt.validate(GOOD)
        self.assertTrue(v["ok"])
        self.assertEqual(v["score"], 100)
        self.assertEqual(v["title"], "Cedar Bench Co.")
        self.assertEqual([s["title"] for s in v["sections"]], ["Products", "Optional"])
        self.assertEqual(v["links"], 3)

    def test_missing_h1_and_summary(self):
        v = llms_txt.validate("## Pages\n\n- [A](https://e.test/a)\n")
        self.assertFalse(v["ok"])
        self.assertTrue(sev(v, "error", "missing H1"))
        self.assertTrue(sev(v, "warning", "summary"))

    def test_h1_not_first_and_two_h1s(self):
        v = llms_txt.validate("> s\n# A\n# B\n")
        self.assertTrue(sev(v, "error", "not the first line"))
        self.assertTrue(sev(v, "error", "more than one H1"))

    def test_link_problems(self):
        text = GOOD + "\n## More\n\n- [Rel](/relative)\n- [Dup](https://example.test/benches/classic)\n- plain item\n\n## Empty\n"
        v = llms_txt.validate(text)
        self.assertTrue(sev(v, "warning", "relative"))
        self.assertTrue(sev(v, "warning", "duplicate URL"))
        self.assertTrue(sev(v, "warning", "not a '[title](url)' link"))
        self.assertTrue(sev(v, "warning", "'Empty' has no links"))

    def test_empty_file(self):
        self.assertFalse(llms_txt.validate("")["ok"])


class LlmsGenerateTest(unittest.TestCase):
    def test_generate_round_trips_valid(self):
        site = {"name": "N", "summary": "S  with   spaces", "sections": [
            {"title": "Docs", "links": [{"title": "A", "url": "https://e.test/a", "desc": "d"}]},
            {"title": "Skipped", "links": []}],
            "optional": [{"title": "B", "url": "https://e.test/b"}]}
        text = llms_txt.generate(site)
        self.assertIn("> S with spaces", text)
        self.assertNotIn("Skipped", text)
        v = llms_txt.validate(text)
        self.assertTrue(v["ok"])
        self.assertEqual(v["score"], 100)

    def test_from_urls_groups_by_segment(self):
        site = llms_txt.site_from_urls(
            ["https://e.test/", "https://e.test/blog/first-post", "https://e.test/blog/second",
             "https://e.test/about", "not-a-url", "https://e.test/"], "N")
        titles = [s["title"] for s in site["sections"]]
        self.assertEqual(titles, ["Main", "Blog"])
        self.assertEqual(site["sections"][1]["links"][0]["title"], "First Post")
        self.assertEqual(len(site["sections"][0]["links"]), 2)   # home + about, deduped

    def test_generate_rejects_nameless(self):
        with self.assertRaises(ValueError):
            llms_txt.generate({"summary": "x"})

    def test_cli(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "llms.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(GOOD)
            r = subprocess.run([sys.executable, os.path.join(SEO, "llms_txt.py"), "--validate", p],
                               capture_output=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0)
            self.assertTrue(json.loads(r.stdout)["ok"])
            r = subprocess.run([sys.executable, os.path.join(SEO, "llms_txt.py"),
                                "--generate", '{"summary": "no name"}'],
                               capture_output=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)


class GeoIntegrationTest(unittest.TestCase):
    TEXT = ("Cedar benches last 15 to 25 years outdoors when oiled once a year, per the "
            "Cedar Growers Council 2025 study.\n\nShipping costs nothing on orders over $200 in "
            "the contiguous US; delivery takes 5 to 7 business days.\n")

    def test_fanout_coverage(self):
        fo = geo_check.fanout_coverage(self.TEXT, [
            "how long do cedar benches last outdoors",
            "how much does shipping cost",
            "is teak better than cedar"])
        self.assertEqual(fo["questions"], 3)
        self.assertEqual([r["covered"] for r in fo["rows"]], [True, True, False])
        self.assertIn("teak", fo["rows"][2]["missing_terms"])
        self.assertEqual(fo["coverage_pct"], 67)

    def test_fanout_deterministic_and_empty(self):
        a = geo_check.fanout_coverage(self.TEXT, ["shipping cost"])
        self.assertEqual(a, geo_check.fanout_coverage(self.TEXT, ["shipping cost"]))
        self.assertIsNone(geo_check.fanout_coverage(self.TEXT, [])["coverage_pct"])

    def test_scorecard_uses_llms_validation(self):
        bad = {"present": True, "validation": llms_txt.validate("no heading here\n")}
        good = {"present": True, "validation": llms_txt.validate(GOOD)}
        for llm, want in ((good, 100), (bad, None)):
            card = geo_check.build_scorecard({"llms_txt": llm})
            cat = [c for c in card["categories"] if c["name"] == "llms_txt"][0]
            if want is None:
                self.assertLessEqual(cat["score"], 60)
            else:
                self.assertEqual(cat["score"], want)

    def test_cli_llms_and_questions_offline(self):
        with tempfile.TemporaryDirectory() as td:
            c, q, l = (os.path.join(td, n) for n in ("c.md", "q.txt", "llms.txt"))
            for path, body in ((c, self.TEXT), (q, "shipping cost\n"), (l, GOOD)):
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(body)
            r = subprocess.run([sys.executable, os.path.join(SEO, "geo_check.py"), "--content", c,
                                "--questions", q, "--llms", l, "--scorecard", "--no-network"],
                               capture_output=True, encoding="utf-8")
            d = json.loads(r.stdout)
            self.assertEqual(d["fanout"]["covered"], 1)
            self.assertTrue(d["llms_txt"]["validation"]["ok"])
            self.assertNotIn("llms_txt", d["geo_score"]["excluded"])


class DriftD15Test(unittest.TestCase):
    HTML = "<html><head><title>T</title></head><body><h1>H</h1></body></html>"

    def test_capture_adds_verdict_only_with_robots(self):
        self.assertNotIn("ai_crawler_verdict", drift_tools.capture(self.HTML))
        snap = drift_tools.capture(self.HTML, robots="User-agent: *\nAllow: /\n")
        self.assertEqual(snap["ai_crawler_verdict"], "fully-open")

    def _d15(self, before, after):
        r = drift_severity.evaluate({"ai_crawler_verdict": before}, {"ai_crawler_verdict": after})
        hits = [c for c in r["regressions"] if c["code"] == "D15"]
        return hits[0]["severity"] if hits else None

    def test_tiers(self):
        self.assertEqual(self._d15("fully-open", "retrieval-blocked"), "critical")
        self.assertEqual(self._d15("citable-training-blocked", "search-engine-blocked"), "critical")
        self.assertEqual(self._d15("fully-open", "retrieval-partial"), "high")
        self.assertEqual(self._d15("fully-open", "citable-training-blocked"), "advisory")
        self.assertEqual(self._d15("retrieval-blocked", "fully-open"), "advisory")
        self.assertIsNone(self._d15("fully-open", "fully-open"))

    def test_absent_on_either_side_is_silent(self):
        r = drift_severity.evaluate({}, {"ai_crawler_verdict": "retrieval-blocked"})
        self.assertEqual(r["regressions"], [])


if __name__ == "__main__":
    unittest.main()
