"""v1.10 site_audit.py -- the seo-audit orchestrator's local one-command path: engine ->
specialist scores -> audit_aggregate health score, covered / not-covered honesty, and one
deduplicated fix list.

Offline, stdlib-only; runs under unittest and pytest.
"""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "workflow", "site_audit.py")
EX = os.path.join(ROOT, "references", "examples")


def run(*args):
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, encoding="utf-8")
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stdout)


class SiteAuditTest(unittest.TestCase):
    def setUp(self):
        rc, self.d = run("--dir", os.path.join(EX, "seo-sitemap", "site"), "--base-url",
                         "https://example.test", "--as-of", "2026-09-25")
        self.assertEqual(rc, 0)

    def test_specialists_and_honest_coverage(self):
        d = self.d
        self.assertEqual(set(d["covered"]), {"seo-content", "seo-geo", "seo-page", "seo-schema",
                                             "seo-sitemap", "seo-technical"})
        for name in ("seo-google", "seo-backlinks", "seo-local-unified", "seo-ecommerce",
                     "seo-hreflang", "seo-image-audit"):
            self.assertIn(name, d["not_covered"])
        self.assertEqual(d["health"]["specialists_count"], 6)
        self.assertTrue(0 <= d["health"]["overall_score"] <= 100)

    def test_health_is_the_reweighted_mean_of_specialists(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
        import audit_aggregate
        again = audit_aggregate.aggregate(self.d["specialists"])
        self.assertEqual(again["overall_score"], self.d["health"]["overall_score"])

    def test_fixes_are_merged_and_ordered(self):
        fixes = self.d["fixes"]
        sev = [f["severity"] for f in fixes]
        self.assertEqual(sev, sorted(sev, key=["critical", "high", "medium"].index))
        thin = [f for f in fixes if "thin for a home page" in f["finding"]]
        self.assertEqual(len(thin), 1)                  # "3 words" / "8 words" merged
        self.assertTrue(thin[0].get("varies_by_page"))
        self.assertTrue(any(f["finding"].startswith("1 orphan page") for f in fixes))

    def test_page_types_follow_url_classes(self):
        # the author rule is article-only: only the /guides/ page is an article here
        authors = [f for f in self.d["fixes"] if "No identifiable author" in f["finding"]]
        self.assertEqual(authors[0]["pages"], ["guides/cedar-care.html"])

    def test_deterministic(self):
        self.assertEqual(self.d, run("--dir", os.path.join(EX, "seo-sitemap", "site"), "--base-url",
                                     "https://example.test", "--as-of", "2026-09-25")[1])


class ConditionalSpecialistsTest(unittest.TestCase):
    def test_hreflang_and_ecommerce_join_when_signals_exist(self):
        rc, d = run("--dir", os.path.join(EX, "seo-hreflang"), "--base-url", "https://example.test")
        self.assertIn("seo-hreflang", d["covered"])
        rc, d = run("--file", os.path.join(EX, "seo-ecommerce", "product.html"),
                    "--url", "https://example.test/p/classic-bench", "--as-of", "2026-09-25")
        self.assertIn("seo-ecommerce", d["covered"])
        self.assertIn("seo-sitemap", d["not_covered"])     # file mode: no build

    def test_bad_input(self):
        self.assertEqual(run("--dir", "/nope", "--base-url", "https://e.test")[0], 1)
        self.assertEqual(run("--file", "/nope.html")[0], 1)


if __name__ == "__main__":
    unittest.main()
