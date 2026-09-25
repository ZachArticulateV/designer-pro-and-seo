"""v1.8 depth: hreflang_tools.py code rules + the cross-page --cluster audit, and
product_audit.py merchant-listing / category index-hygiene checks.

Offline, stdlib-only; runs under unittest and pytest.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEO = os.path.join(ROOT, "scripts", "seo")
HX = os.path.join(ROOT, "references", "examples", "seo-hreflang")
EX = os.path.join(ROOT, "references", "examples", "seo-ecommerce")
sys.path.insert(0, SEO)
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
import hreflang_tools as ht  # noqa: E402
import product_audit as pa  # noqa: E402


def codes(r, key="issues"):
    return {i["code"] for i in r[key]}


class CodeRulesTest(unittest.TestCase):
    def test_valid(self):
        for c in ("en", "en-US", "en-us", "zh-Hant-TW", "zh-Hans", "se", "x-default", "pt-BR"):
            self.assertTrue(ht.validate_code(c)[0], c)

    def test_classic_mistakes(self):
        for c, needle in (("en-uk", "'GB'"), ("jp", "'ja'"), ("es-419", "numeric"),
                          ("en-EU", "not a country"), ("en-us-x", "too many"), ("xx", "ISO 639-1")):
            ok, msg = ht.validate_code(c)
            self.assertFalse(ok, c)
            self.assertIn(needle, msg, c)


def page(url, alts, lang="en", canonical=None, noindex=False):
    links = "".join('<link rel="alternate" hreflang="%s" href="%s">' % a for a in alts)
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    return ('<html lang="%s"><head><link rel="canonical" href="%s">%s%s</head></html>'
            % (lang, canonical or url, links, robots))


class ClusterTest(unittest.TestCase):
    A, B = "https://e.test/", "https://e.test/fr/"

    def _cluster(self, a_html, b_html):
        return ht.cluster({self.A: ht.extract_page(a_html), self.B: ht.extract_page(b_html)})

    def test_clean_cluster(self):
        alts = [("en", self.A), ("fr", self.B), ("x-default", self.A)]
        r = self._cluster(page(self.A, alts), page(self.B, alts, lang="fr"))
        self.assertEqual(r["issues"], [])
        self.assertEqual(r["score"], 100)

    def test_return_link_self_ref_and_code_conflict(self):
        r = self._cluster(page(self.A, [("en", self.A), ("fr", self.B), ("x-default", self.A)]),
                          page(self.B, [("fr", self.B), ("x-default", self.A)], lang="fr"))
        self.assertIn("H7", codes(r))
        r = self._cluster(page(self.A, [("fr", self.B), ("x-default", self.A)]),
                          page(self.B, [("en", self.A), ("fr", self.B), ("x-default", self.A)], lang="fr"))
        self.assertIn("H3", codes(r))
        r = self._cluster(page(self.A, [("en", self.A), ("fr-fr", self.B), ("x-default", self.A)]),
                          page(self.B, [("en", self.A), ("fr-ca", self.B), ("x-default", self.A)], lang="fr"))
        self.assertIn("H8", codes(r))

    def test_noindex_canonical_lang_and_xdefault(self):
        alts = [("en", self.A), ("de", self.B)]
        r = self._cluster(page(self.A, alts + [("x-default", self.A)]),
                          page(self.B, alts + [("x-default", self.B)], lang="en",
                               canonical=self.A, noindex=True))
        self.assertTrue({"H9", "H10", "H11", "H12"} <= codes(r))

    def test_golden_manifest_and_files(self):
        r = ht.cluster(ht._load_cluster([os.path.join(HX, "manifest.json")]))
        self.assertEqual(codes(r), {"H2", "H4", "H6", "H7", "H9", "H12"})
        self.assertEqual(r["score"], 68)
        files = [os.path.join(HX, f) for f in ("en.html", "fr.html", "de.html")]
        self.assertEqual(ht.cluster(ht._load_cluster(files))["score"], 68)

    def test_cli_needs_canonical_without_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x.html")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("<html><head></head></html>")
            r = subprocess.run([sys.executable, os.path.join(SEO, "hreflang_tools.py"), "--cluster", p],
                               capture_output=True, encoding="utf-8")
            self.assertEqual(r.returncode, 1)


def product_html(product, body="<h1>Bench</h1><p>" + "cedar " * 200 + "</p>", org=None):
    graph = [product] + ([org] if org else [])
    return ('<html><head><script type="application/ld+json">%s</script></head><body>%s</body></html>'
            % (json.dumps({"@context": "https://schema.org", "@graph": graph}), body))


GOOD = {"@type": "Product", "name": "Bench", "image": "https://e.test/b.jpg", "gtin13": "0123456789012",
        "brand": {"@type": "Brand", "name": "B"},
        "offers": {"@type": "Offer", "price": "49.99", "priceCurrency": "USD",
                   "availability": "https://schema.org/InStock",
                   "shippingDetails": {"@type": "OfferShippingDetails", "shippingDestination": "US"}}}
ORG = {"@type": "Organization", "name": "B", "url": "https://e.test/",
       "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy", "applicableCountry": "US",
                                   "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow"}}


class ProductTest(unittest.TestCase):
    def test_clean_product_with_org_level_returns(self):
        r = pa.audit(product_html(GOOD, body="<h1>Bench</h1><p>$49.99 " + "cedar " * 200 + "</p>", org=ORG))
        self.assertEqual(r["findings"], [])
        self.assertEqual(r["score"], 100)

    def test_price_visibility_requires_cents(self):
        self.assertTrue(pa._price_visible("49.99", "now $49.99 only"))
        self.assertFalse(pa._price_visible("49.99", "now $49 only"))
        self.assertTrue(pa._price_visible("1299", "just $1,299.00"))
        self.assertFalse(pa._price_visible("349", "was $3490"))

    def test_no_markup_and_missing_ids(self):
        self.assertIn("P1", codes(pa.audit("<html><body><h1>x</h1></body></html>", page_type="product"),
                                  "findings"))
        bare = dict(GOOD, gtin13=None, brand=None)
        r = pa.audit(product_html(bare, body="<h1>B</h1><p>$49.99 " + "w " * 200 + "</p>", org=ORG))
        self.assertIn("P5", codes(r, "findings"))

    def test_expired_and_stale_markup(self):
        prod = json.loads(json.dumps(GOOD))
        prod["offers"]["priceValidUntil"] = "2026-01-01"
        r = pa.audit(product_html(prod, body="<h1>B</h1><p>$49.99 sold out " + "w " * 200 + "</p>", org=ORG),
                     as_of=dt.date(2026, 9, 25))
        self.assertTrue({"P8", "P11"} <= codes(r, "findings"))

    def test_golden_product(self):
        html = open(os.path.join(EX, "product.html"), encoding="utf-8").read()
        r = pa.audit(html, "https://example.test/p/classic-bench", as_of=dt.date(2026, 9, 25))
        self.assertEqual(codes(r, "findings"),
                         {"P4", "P6", "P7", "P8", "P9", "P10", "P11", "P12", "P14"})
        self.assertEqual(r["score"], 40)
        self.assertEqual(r["findings"][0]["code"], "P8")     # numeric sort within severity


class CategoryTest(unittest.TestCase):
    def test_golden_category(self):
        html = open(os.path.join(EX, "category.html"), encoding="utf-8").read()
        r = pa.audit(html, "https://example.test/benches?color=red&page=2")
        self.assertEqual(r["page_type"], "category")
        self.assertEqual(codes(r, "findings"), {"C2", "C4", "C6"})
        self.assertEqual(r["score"], 86)

    def test_facet_and_sort_bloat(self):
        body = "<h1>Benches</h1><p>" + "w " * 100 + "</p>"
        html = '<html><head><link rel="canonical" href="https://e.test/b?color=red&sort=price"></head><body>%s</body></html>' % body
        r = pa.audit(html, "https://e.test/b?color=red&sort=price", page_type="category")
        self.assertTrue({"C1", "C5"} <= codes(r, "findings"))
        noidx = html.replace("<head>", '<head><meta name="robots" content="noindex">')
        self.assertFalse({"C1", "C5"} & codes(pa.audit(noidx, "https://e.test/b?color=red&sort=price",
                                                       page_type="category"), "findings"))

    def test_cli_bad_input(self):
        r = subprocess.run([sys.executable, os.path.join(SEO, "product_audit.py"), "--file", "/nope"],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
