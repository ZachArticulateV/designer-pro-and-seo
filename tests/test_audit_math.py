"""Tests for the audit-math trio the W4 seo-audit socket consumes:

  scripts/seo/business_type.py    -- classify a site into a business type + vertical
  scripts/seo/crawl_inventory.py  -- bucket a discovered-URL list into an inventory
  scripts/workflow/audit_aggregate.py -- re-normalized overall health score

Contract (all three): JSON to stdout by default; `--human` ASCII summary;
deterministic (same input -> same output); bad input -> JSON error object + a
NON-ZERO exit (never a raw traceback); offline (no network anywhere here).

Runs under BOTH `py -m unittest discover -s tests` and `pytest tests/`, no pip
install, no network. Fixtures live in a tempdir.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEO = os.path.join(ROOT, "scripts", "seo")
WF = os.path.join(ROOT, "scripts", "workflow")


def _run(script_path, args, stdin=None):
    """Run a backbone script as a subprocess; return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, script_path] + args,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _is_ascii(text):
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


# --------------------------------------------------------------------------- #
# business_type.py
# --------------------------------------------------------------------------- #
class BusinessTypeTest(unittest.TestCase):
    SCRIPT = os.path.join(SEO, "business_type.py")

    SAAS = {
        "schema_types": ["SoftwareApplication", "Organization"],
        "keywords": ["free trial", "sign up", "pricing", "api", "integrations",
                     "dashboard"],
        "has_pricing": True,
        "has_subscription": True,
        "page_types": {"pricing": 1, "features": 4, "blog": 8},
    }
    ECOM = {
        "schema_types": ["Product", "Offer", "AggregateRating"],
        "keywords": ["add to cart", "checkout", "free shipping", "buy now"],
        "has_cart": True,
        "page_types": {"product": 240, "category": 30, "blog": 4},
    }

    def _classify(self, signals, extra=None):
        rc, out, err = _run(self.SCRIPT, ["--signals", json.dumps(signals)]
                            + (extra or []))
        return rc, out, err

    def test_saas_classified(self):
        rc, out, _ = self._classify(self.SAAS)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["business_type"], "saas")

    def test_ecommerce_classified(self):
        rc, out, _ = self._classify(self.ECOM)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["business_type"], "ecommerce")

    def test_saas_and_ecommerce_differ(self):
        _, saas_out, _ = self._classify(self.SAAS)
        _, ecom_out, _ = self._classify(self.ECOM)
        self.assertNotEqual(
            json.loads(saas_out)["business_type"],
            json.loads(ecom_out)["business_type"],
        )

    def test_confidence_in_unit_range(self):
        _, out, _ = self._classify(self.SAAS)
        conf = json.loads(out)["confidence"]
        self.assertIsInstance(conf, (int, float))
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    def test_drivers_reported(self):
        # the signals that drove the decision must be surfaced, not fabricated
        _, out, _ = self._classify(self.ECOM)
        data = json.loads(out)
        self.assertIn("drivers", data)
        self.assertTrue(len(data["drivers"]) >= 1)

    def test_vertical_present(self):
        _, out, _ = self._classify(self.ECOM)
        self.assertIn("vertical", json.loads(out))

    def test_no_signals_is_unknown_not_fabricated(self):
        # empty-but-valid signal object: must NOT invent a type with high confidence
        rc, out, _ = self._classify({})
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["business_type"], "unknown")
        self.assertEqual(data["confidence"], 0.0)

    def test_deterministic(self):
        _, a, _ = self._classify(self.SAAS)
        _, b, _ = self._classify(self.SAAS)
        self.assertEqual(a, b)

    def test_file_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "signals.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(self.SAAS, fh)
            rc, out, _ = _run(self.SCRIPT, ["--file", p])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out)["business_type"], "saas")

    def test_human_is_ascii(self):
        rc, out, _ = self._classify(self.SAAS, extra=["--human"])
        self.assertEqual(rc, 0)
        self.assertTrue(_is_ascii(out))
        self.assertIn("saas", out.lower())

    def test_bad_json_nonzero_with_error_object(self):
        rc, out, err = _run(self.SCRIPT, ["--signals", "{not valid json"])
        self.assertNotEqual(rc, 0)
        # a JSON error object on stdout, never a raw traceback
        data = json.loads(out)
        self.assertIn("error", data)
        self.assertNotIn("Traceback", err)

    def test_missing_input_nonzero(self):
        rc, out, _ = _run(self.SCRIPT, [])
        self.assertNotEqual(rc, 0)
        self.assertIn("error", json.loads(out))


# --------------------------------------------------------------------------- #
# crawl_inventory.py
# --------------------------------------------------------------------------- #
class CrawlInventoryTest(unittest.TestCase):
    SCRIPT = os.path.join(SEO, "crawl_inventory.py")

    URLS = [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/contact",
        "https://example.com/blog/hello-world",
        "https://example.com/blog/second-post",
        "https://example.com/products/widget-a",
        "https://example.com/products/widget-b",
        "https://example.com/products/widget-c",
    ]

    def _urls_file(self, d, urls=None):
        p = os.path.join(d, "urls.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("\n".join(self.URLS if urls is None else urls))
        return p

    def test_buckets_and_counts(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._urls_file(d)
            rc, out, _ = _run(self.SCRIPT, ["--urls", p])
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertEqual(data["total"], 8)
            buckets = data["buckets"]
            self.assertEqual(buckets.get("home"), 1)
            self.assertEqual(buckets.get("blog"), 2)
            self.assertEqual(buckets.get("product"), 3)

    def test_depth_reported(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._urls_file(d)
            _, out, _ = _run(self.SCRIPT, ["--urls", p])
            data = json.loads(out)
            # home is depth 0; /products/widget-a is depth 2
            self.assertIn("depth_distribution", data)
            self.assertGreaterEqual(data["max_depth"], 2)

    def test_stdin_input(self):
        rc, out, _ = _run(self.SCRIPT, ["--urls", "-"],
                          stdin="\n".join(self.URLS))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["total"], 8)

    def test_json_array_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "urls.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(self.URLS, fh)
            rc, out, _ = _run(self.SCRIPT, ["--urls", p])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out)["total"], 8)

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._urls_file(d)
            _, a, _ = _run(self.SCRIPT, ["--urls", p])
            _, b, _ = _run(self.SCRIPT, ["--urls", p])
            self.assertEqual(a, b)

    def test_human_is_ascii(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._urls_file(d)
            rc, out, _ = _run(self.SCRIPT, ["--urls", p, "--human"])
            self.assertEqual(rc, 0)
            self.assertTrue(_is_ascii(out))

    def test_missing_file_nonzero(self):
        rc, out, err = _run(self.SCRIPT, ["--urls", "/no/such/file.txt"])
        self.assertNotEqual(rc, 0)
        self.assertIn("error", json.loads(out))
        self.assertNotIn("Traceback", err)

    def test_no_valid_urls_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._urls_file(d, urls=["", "   ", "# just a comment"])
            rc, out, _ = _run(self.SCRIPT, ["--urls", p])
            self.assertNotEqual(rc, 0)
            self.assertIn("error", json.loads(out))


# --------------------------------------------------------------------------- #
# audit_aggregate.py
# --------------------------------------------------------------------------- #
class AuditAggregateTest(unittest.TestCase):
    SCRIPT = os.path.join(WF, "audit_aggregate.py")

    def _agg(self, scores, extra=None):
        rc, out, err = _run(self.SCRIPT, ["--scores", json.dumps(scores)]
                           + (extra or []))
        return rc, out, err

    def test_single_specialist_is_its_own_score(self):
        # re-normalization: one present specialist normalizes to weight 1.0,
        # so the overall is exactly that specialist's score -- NOT dragged toward
        # zero by the specialists that were skipped.
        rc, out, _ = self._agg({"seo-technical": 80})
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["overall_score"], 80.0)
        self.assertEqual(data["specialists_count"], 1)

    def test_renormalizes_over_present_only(self):
        # two equally-weighted specialists -> simple average of their scores,
        # regardless of how many other specialists exist in the weight table.
        rc, out, _ = self._agg({"seo-technical": 80, "seo-page": 90})
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["overall_score"], 85.0)
        self.assertEqual(sorted(data["specialists_present"]),
                         ["seo-page", "seo-technical"])

    def test_absent_specialist_does_not_zero_score(self):
        # adding a third (absent) specialist must NOT change the score of the
        # two that ran -- the proof that skipping is not a silent zero.
        _, two, _ = self._agg({"seo-technical": 80, "seo-page": 90})
        # same two run; a third is simply not in the map
        self.assertEqual(json.loads(two)["overall_score"], 85.0)

    def test_object_score_form(self):
        # a specialist may report {"score": N, "findings": [...]}
        rc, out, _ = self._agg({
            "seo-technical": {"score": 70, "findings": ["x"]},
            "seo-page": {"score": 90},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["overall_score"], 80.0)

    def test_breakdown_present(self):
        _, out, _ = self._agg({"seo-technical": 80, "seo-page": 90})
        data = json.loads(out)
        self.assertIn("breakdown", data)
        self.assertEqual(len(data["breakdown"]), 2)
        # normalized weights sum to 1.0 over present specialists
        nw = sum(b["normalized_weight"] for b in data["breakdown"])
        self.assertAlmostEqual(nw, 1.0, places=6)

    def test_deterministic(self):
        _, a, _ = self._agg({"seo-technical": 80, "seo-page": 90})
        _, b, _ = self._agg({"seo-technical": 80, "seo-page": 90})
        self.assertEqual(a, b)

    def test_file_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "scores.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"seo-technical": 80, "seo-page": 90}, fh)
            rc, out, _ = _run(self.SCRIPT, ["--file", p])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out)["overall_score"], 85.0)

    def test_missing_file_nonzero_with_json_error(self):
        rc, out, err = _run(self.SCRIPT, ["--file", "/no/such/scores.json"])
        self.assertNotEqual(rc, 0)
        self.assertIn("error", json.loads(out))
        self.assertNotIn("Traceback", err)

    def test_human_is_ascii(self):
        rc, out, _ = self._agg({"seo-technical": 80, "seo-page": 90},
                               extra=["--human"])
        self.assertEqual(rc, 0)
        self.assertTrue(_is_ascii(out))

    def test_bad_json_nonzero(self):
        rc, out, err = _run(self.SCRIPT, ["--scores", "{nope"])
        self.assertNotEqual(rc, 0)
        self.assertIn("error", json.loads(out))
        self.assertNotIn("Traceback", err)

    def test_empty_map_nonzero(self):
        rc, out, _ = self._agg({})
        self.assertNotEqual(rc, 0)
        self.assertIn("error", json.loads(out))

    def test_out_of_range_score_nonzero(self):
        rc, out, _ = self._agg({"seo-technical": 150})
        self.assertNotEqual(rc, 0)
        self.assertIn("error", json.loads(out))

    def test_non_numeric_score_nonzero(self):
        rc, out, _ = self._agg({"seo-technical": "great"})
        self.assertNotEqual(rc, 0)
        self.assertIn("error", json.loads(out))


if __name__ == "__main__":
    unittest.main()
