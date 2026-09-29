"""schema_gen.py depth (v1.3) -- nested validation, value rules, @graph, the cross-page
@id entity graph, the --site starter, and the golden example scores.

Offline, stdlib-only; runs under unittest and pytest.
"""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "seo", "schema_gen.py")
EX = os.path.join(ROOT, "references", "examples", "seo-schema")
sys.path.insert(0, os.path.join(ROOT, "scripts", "seo"))
import schema_gen as sg  # noqa: E402

CTX = "https://schema.org"


def issues(obj):
    return sg.validate_obj(obj)["issues"]


def has(iss, sev, needle):
    return any(i["severity"] == sev and needle in i["finding"] for i in iss)


class BackCompatTest(unittest.TestCase):
    def test_legacy_keys_and_article_ok(self):
        v = sg.validate_obj({"@context": CTX, "@type": "Article", "headline": "H",
                             "author": "A", "datePublished": "2026-01-01"})
        for k in ("type", "missing_required", "missing_recommended", "warnings", "ok"):
            self.assertIn(k, v)
        self.assertTrue(v["ok"])

    def test_missing_required_not_ok(self):
        v = sg.validate_obj({"@context": CTX, "@type": "Article", "headline": "H"})
        self.assertFalse(v["ok"])
        self.assertIn("author", v["missing_required"])

    def test_retired_types_flagged_info_not_error(self):
        for t, extra in (("FAQPage", {"mainEntity": []}), ("HowTo", {"name": "n", "step": ["s"]})):
            obj = dict({"@context": CTX, "@type": t}, **extra)
            obj.update({k: "x" for k in sg.SPEC[t]["required"] if not obj.get(k)})
            v = sg.validate_obj(obj)
            self.assertTrue(v["ok"], t)
            self.assertTrue(has(v["issues"], "info", "retired rich result"), t)
            self.assertTrue(any("DEPRECATED" in w for w in v["warnings"]))


class RulesTest(unittest.TestCase):
    def test_product_needs_one_of_offers_review_rating(self):
        v = sg.validate_obj({"@context": CTX, "@type": "Product", "name": "n",
                             "image": "https://e.test/i.jpg"})
        self.assertFalse(v["ok"])
        self.assertTrue(has(v["issues"], "high", "at least one of offers"))

    def test_nested_offer_values(self):
        iss = issues({"@context": CTX, "@type": "Product", "name": "n",
                      "image": "https://e.test/i.jpg",
                      "offers": {"@type": "Offer", "price": "1,299.00", "priceCurrency": "$",
                                 "availability": "https://schema.org/InStock",
                                 "itemCondition": "mint"}})
        self.assertTrue(has(iss, "high", "not a plain number"))
        self.assertTrue(has(iss, "high", "ISO 4217"))
        self.assertTrue(has(iss, "medium", "itemCondition"))
        self.assertFalse(has(iss, "medium", "availability"))
        self.assertTrue(any(i["property"].startswith("offers.") for i in iss))

    def test_untyped_nested_value_uses_parent_spec(self):
        iss = issues({"@context": CTX, "@type": "Product", "name": "n",
                      "image": "https://e.test/i.jpg", "offers": {"price": "5"}})
        self.assertTrue(has(iss, "high", "missing required priceCurrency"))

    def test_nested_review_skips_item_reviewed(self):
        iss = issues({"@context": CTX, "@type": "Product", "name": "n",
                      "image": "https://e.test/i.jpg",
                      "review": {"@type": "Review", "author": {"@type": "Person", "name": "a"},
                                 "reviewRating": {"@type": "Rating", "ratingValue": 5}}})
        self.assertFalse(has(iss, "high", "itemReviewed"))

    def test_rating_bounds_and_counts(self):
        iss = issues({"@context": CTX, "@type": "AggregateRating", "ratingValue": 9,
                      "reviewCount": 0})
        self.assertTrue(has(iss, "high", "outside 1..5"))
        self.assertTrue(has(iss, "high", "positive integer"))

    def test_dates(self):
        iss = issues({"@context": CTX, "@type": "Article", "headline": "h", "author": "a",
                      "datePublished": "2026-05-01", "dateModified": "2026-04-01"})
        self.assertTrue(has(iss, "medium", "earlier than datePublished"))
        iss = issues({"@context": CTX, "@type": "Event", "name": "n", "location": "x",
                      "startDate": "Sept 25, 2026"})
        self.assertTrue(has(iss, "medium", "not ISO 8601"))

    def test_subtype_inheritance(self):
        self.assertEqual(sg.spec_type("BlogPosting"), "Article")
        self.assertEqual(sg.spec_type("Dentist"), "LocalBusiness")
        self.assertIsNone(sg.spec_type("Thing"))
        v = sg.validate_obj({"@context": CTX, "@type": "Dentist", "name": "d"})
        self.assertIn("address", v["missing_required"])

    def test_context_and_unknown_type(self):
        v = sg.validate_obj({"@type": "Person", "name": "p"})
        self.assertTrue(has(v["issues"], "high", '@context'))
        v = sg.validate_obj({"@context": CTX, "@type": "Thing", "name": "t"})
        self.assertTrue(v["ok"])

    def test_graph_members_inherit_context(self):
        res = sg.validate_doc({"@context": CTX, "@graph": [{"@type": "Person", "name": "p"}]})
        self.assertTrue(res[0]["ok"])


class GraphTest(unittest.TestCase):
    def test_dangling_conflict_and_split(self):
        a = {"@context": CTX, "@graph": [
            {"@type": "Organization", "@id": "https://e.test/#organization", "name": "n",
             "url": "https://e.test/"},
            {"@type": "WebSite", "@id": "https://e.test/#website", "name": "n",
             "url": "https://e.test/", "publisher": {"@id": "https://e.test/#org"}}]}
        b = {"@context": CTX, "@graph": [
            {"@type": "Organization", "@id": "https://e.test/#brand", "name": "n",
             "url": "https://e.test/"},
            {"@type": "Person", "@id": "https://e.test/#website", "name": "x"}]}
        r = sg.graph_check({"a": [a], "b": [b]})
        self.assertIn("https://e.test/#org", r["unresolved"])
        self.assertFalse(r["ok"])
        f = " | ".join(i["finding"] for i in r["issues"])
        self.assertIn("conflicting types", f)
        self.assertIn("entity split", f)

    def test_missing_hub_entities(self):
        r = sg.graph_check({"p": [{"@context": CTX, "@type": "Person", "name": "x"}]})
        f = " | ".join(i["finding"] for i in r["issues"])
        self.assertIn("no Organization", f)
        self.assertIn("no WebSite", f)

    def test_site_starter_is_clean_and_linked(self):
        doc = sg.site_graph({"name": "N", "url": "https://e.test",
                             "page": {"url": "https://e.test/p", "name": "P",
                                      "breadcrumb": [["Home", "https://e.test/"], ["P"]]}})
        self.assertTrue(all(r["ok"] for r in sg.validate_doc(doc)))
        g = sg.graph_check({"s": [doc]})
        self.assertEqual(g["unresolved"], [])
        self.assertEqual(g["score"], 100)


class CliGoldenTest(unittest.TestCase):
    def _run(self, *args):
        r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True,
                           encoding="utf-8")
        return r.returncode, r.stdout

    def test_golden_validation_score(self):
        rc, out = self._run("--html", os.path.join(EX, "product.html"))
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertEqual(d["score"], 68)
        self.assertEqual(d["detected"], ["BreadcrumbList", "FAQPage", "Product"])
        self.assertEqual(d["deprecations"], ["FAQPage"])

    def test_golden_graph_score(self):
        rc, out = self._run("--graph-check", os.path.join(EX, "home.html"),
                            os.path.join(EX, "product.html"))
        d = json.loads(out)
        self.assertEqual(d["unresolved"], ["https://example.test/#org"])
        self.assertEqual(d["score"], 90)

    def test_html_without_blocks_and_bad_json(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x.html")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write('<script type="application/ld+json">{nope</script>')
            d = json.loads(self._run("--html", p)[1])
            self.assertFalse(d["ok"])
            self.assertTrue(d["errors"])
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("<p>no markup</p>")
            d = json.loads(self._run("--html", p)[1])
            self.assertIn("no application/ld+json blocks found", d["errors"])

    def test_bad_inputs_exit_nonzero(self):
        self.assertEqual(self._run("--validate", "{bad")[0], 1)
        self.assertEqual(self._run("--site", '{"name": "x"}')[0], 1)
        self.assertEqual(self._run()[0], 2)


if __name__ == "__main__":
    unittest.main()
