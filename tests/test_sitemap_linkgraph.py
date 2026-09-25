"""v1.6 seo-sitemap depth: sitemap_tools.py validation honesty checks + extensions +
quality-gate crosscheck, and link_graph.py internal-link architecture.

Offline, stdlib-only (--check-live is exercised only on its SSRF refusal path).
"""
import datetime as dt
import gzip
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEO = os.path.join(ROOT, "scripts", "seo")
EX = os.path.join(ROOT, "references", "examples", "seo-sitemap")
sys.path.insert(0, SEO)
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
import link_graph as lg  # noqa: E402
import sitemap_tools as st  # noqa: E402

HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'


def urlset(body, extra_ns=""):
    return HEAD + extra_ns + ">" + body + "</urlset>"


def url(loc, lastmod=None, extra=""):
    lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    return f"<url><loc>{loc}</loc>{lm}{extra}</url>"


def codes(r):
    return {i["code"] for i in r["issues"]}


class ValidateTest(unittest.TestCase):
    def test_golden_clean(self):
        r = st.validate(os.path.join(EX, "sample-sitemap.xml"), dt.date(2026, 9, 25))
        self.assertTrue(r["valid"])
        self.assertEqual(r["score"], 100)
        self.assertEqual(r["url_count"], 3)

    def test_hosts_schemes_dups_fragments_params(self):
        r = st.validate(urlset(url("https://a.test/") + url("http://a.test/x") +
                               url("https://b.test/") + url("https://a.test/") +
                               url("https://a.test/p#top") + url("https://a.test/q?utm_source=x")))
        self.assertTrue({"S07", "S08", "S09", "S10", "S11"} <= codes(r))
        self.assertTrue(r["valid"])        # hygiene problems, not protocol violations

    def test_lastmod_honesty(self):
        same = "".join(url(f"https://a.test/{i}", "2026-09-01") for i in range(20))
        r = st.validate(urlset(same + url("https://a.test/f", "2027-01-01") +
                               url("https://a.test/b", "Sept 1")), dt.date(2026, 9, 25))
        self.assertTrue({"S12", "S13", "S14"} <= codes(r))
        r = st.validate(urlset(url("https://a.test/") +
                               "<url><loc>https://a.test/x</loc><changefreq>daily</changefreq></url>"))
        self.assertTrue({"S15", "S16"} <= codes(r))

    def test_protocol_errors(self):
        r = st.validate(urlset(url("/relative")))
        self.assertFalse(r["valid"])
        self.assertIn("S06", codes(r))
        self.assertFalse(st.validate("<urlset><oops>")["valid"])
        self.assertFalse(st.validate(urlset(""))["valid"])

    def test_extensions(self):
        ns = (' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
              ' xmlns:video="http://www.google.com/schemas/sitemap-video/1.1"'
              ' xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"'
              ' xmlns:xhtml="http://www.w3.org/1999/xhtml"')
        body = (url("https://a.test/", extra="<image:image><image:loc>/rel.jpg</image:loc></image:image>"
                    "<video:video><video:title>t</video:title></video:video>"
                    "<news:news><news:title>t</news:title><news:publication_date>2026-09-01"
                    "</news:publication_date></news:news>"
                    '<xhtml:link rel="alternate" hreflang="de" href="https://a.test/de/"/>'))
        r = st.validate(urlset(body, ns), dt.date(2026, 9, 25))
        self.assertTrue({"S20", "S21", "S23", "S24", "S26"} <= codes(r))

    def test_gzip_and_index(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.xml.gz")
            with open(p, "wb") as fh:
                fh.write(gzip.compress(urlset(url("https://a.test/")).encode()))
            self.assertTrue(st.validate(p)["valid"])
        idx = ('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               "<sitemap><loc>child.xml</loc></sitemap></sitemapindex>")
        self.assertIn("S06", codes(st.validate(idx)))

    def test_generate_dedupes_and_warns_on_blanket_lastmod(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "s.xml")
            r = st.generate(["https://a.test/", "https://a.test/", "ftp://x"], out, "2026-09-01")
            self.assertEqual(r["url_count"], 1)
            self.assertTrue(any("duplicate" in w for w in r["warnings"]))
            self.assertTrue(any("lastmod-file" in w for w in r["warnings"]))
            r = st.generate(["https://a.test/"], out, lastmods={"https://a.test/": "2026-01-02"})
            self.assertIn("2026-01-02", open(out, encoding="utf-8").read())


class CrosscheckTest(unittest.TestCase):
    def test_golden_gates(self):
        locs = st.sitemap_locs(os.path.join(EX, "sample-sitemap.xml"))
        pages = json.load(open(os.path.join(EX, "pages.json"), encoding="utf-8"))
        r = st.crosscheck(locs, pages)
        self.assertEqual({i["code"] for i in r["issues"]}, {"G2", "G4", "G5"})
        self.assertEqual(r["score"], 82)
        self.assertFalse(r["ok"])

    def test_non200_noindex_and_missing_state(self):
        r = st.crosscheck(["https://a.test/x", "https://a.test/y", "https://a.test/z"],
                          [{"url": "https://a.test/x", "status": 404},
                           {"url": "https://a.test/y", "status": 200, "noindex": True}])
        self.assertTrue({"G1", "G3", "G0"} <= {i["code"] for i in r["issues"]})

    def test_check_live_refuses_internal_hosts(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.xml")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(urlset(url("http://127.0.0.1/")))
            r = subprocess.run([sys.executable, os.path.join(SEO, "sitemap_tools.py"),
                                "--check-live", p, "--sample", "1"],
                               capture_output=True, encoding="utf-8")
            d = json.loads(r.stdout)
            self.assertIsNone(d["pages"][0]["status"])
            self.assertIn("error", d["pages"][0])
            self.assertIn("fetched 1 of 1", d["sampling"])


class LinkGraphTest(unittest.TestCase):
    def test_golden_site(self):
        pages = lg.pages_from_dir(os.path.join(EX, "site"), "https://example.test")
        r = lg.analyze(pages, "https://example.test")
        self.assertEqual(r["pages"], 9)
        self.assertEqual(r["max_depth"], 5)
        self.assertEqual({i["code"] for i in r["issues"]}, {"L1", "L3", "L4", "L5", "L6", "L7"})
        self.assertEqual(r["score"], 64)
        orphan = [i for i in r["issues"] if i["code"] == "L1"][0]
        self.assertEqual(orphan["urls"], ["https://example.test/guides/cedar-care.html"])

    def test_norm(self):
        self.assertEqual(lg.norm("HTTPS://E.test/a/index.html#x"), "https://e.test/a")
        self.assertEqual(lg.norm("https://e.test/"), "https://e.test/")
        self.assertEqual(lg.norm("https://e.test/b/?q=1"), "https://e.test/b?q=1")

    def test_edges_mode_islands_nofollow_and_sitemap_parity(self):
        edges = {"https://e.test/": ["/a"], "https://e.test/a": ["/"],
                 "https://e.test/b": ["/c"], "https://e.test/c": ["/b", "/gone"]}
        pages = lg.pages_from_edges(edges)
        pages["https://e.test/a"].append({"to": "https://e.test/", "rel": "nofollow",
                                          "chrome": False, "text": "home"})
        r = lg.analyze(pages, "https://e.test/", complete=False,
                       sitemap=["https://e.test/", "https://e.test/b"])
        c = {i["code"] for i in r["issues"]}
        self.assertIn("L2", c)                      # b <-> c island
        self.assertIn("L8", c)
        self.assertIn("L10", c)
        broken = [i for i in r["issues"] if i["code"] == "L3"][0]
        self.assertEqual(broken["severity"], "info")    # incomplete set -> not asserted broken

    def test_cli(self):
        r = subprocess.run([sys.executable, os.path.join(SEO, "link_graph.py"), "--dir",
                            os.path.join(EX, "site"), "--base-url", "https://example.test",
                            "--sitemap", os.path.join(EX, "sample-sitemap.xml")],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0)
        self.assertIn("L10", {i["code"] for i in json.loads(r.stdout)["issues"]})
        r = subprocess.run([sys.executable, os.path.join(SEO, "link_graph.py"), "--dir", "/nope"],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
