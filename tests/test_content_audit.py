"""content_audit.py (v1.5) -- the deterministic content-quality audit behind seo-page and
seo-content. One signal per case, plus the golden example, format detection and CLI.

Offline, stdlib-only; runs under unittest and pytest.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "seo", "content_audit.py")
GOLDEN = os.path.join(ROOT, "references", "examples", "seo-content", "sample-article.html")
sys.path.insert(0, os.path.join(ROOT, "scripts", "seo"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
import content_audit as ca  # noqa: E402

FILLER_P = ("<p>" + " ".join(["Cedar benches are built from kiln-dried boards by our small team."] * 1)
            + "</p>")


def html(body, head="", title="Cedar Bench Care Guide"):
    return ("<!DOCTYPE html><html><head><title>%s</title>%s</head><body>"
            "<footer><a href='/about'>About</a><a href='/contact'>Contact</a></footer>"
            "%s</body></html>" % (title, head, body))


def long_para(n=80, word="cedar"):
    return "<p>" + " ".join(["The %s bench lasts for years outdoors." % word] * (n // 6)) + "</p>"


def has(r, dim, sev, needle):
    return any(c["dimension"] == dim and c["severity"] == sev and needle in c["finding"]
               for c in r["checks"])


class EeatTest(unittest.TestCase):
    def test_byline_sources(self):
        r = ca.audit(html("<h1>Care</h1>" + long_para()))
        self.assertTrue(has(r, "eeat", "high", "No identifiable author"))
        for head in ('<meta name="author" content="Ada Wren">',
                     '<script type="application/ld+json">{"@type":"Article","author":'
                     '{"@type":"Person","name":"Ada Wren"}}</script>'):
            r = ca.audit(html("<h1>Care</h1>" + long_para(), head=head))
            self.assertTrue(has(r, "eeat", "info", "byline: Ada Wren"), head)
        r = ca.audit(html("<h1>Care</h1><p>By Ada Wren</p>" + long_para()))
        self.assertTrue(has(r, "eeat", "info", "byline: Ada Wren"))

    def test_ymyl_requires_credentials(self):
        body = ("<h1>Treatment</h1><p>Addiction treatment and therapy for anxiety and "
                "depression, with medication support and detox.</p>" + long_para())
        r = ca.audit(html(body))
        self.assertTrue(r["ymyl"])
        self.assertTrue(has(r, "eeat", "high", "no credentials"))
        r = ca.audit(html(body + "<p>Clinically reviewed by Jo Lark, LCSW.</p>"))
        self.assertFalse(has(r, "eeat", "high", "no credentials"))
        self.assertFalse(ca.audit(html(body), ymyl="no")["ymyl"])

    def test_dates_staleness_and_order(self):
        head = ('<script type="application/ld+json">{"@type":"Article","datePublished":'
                '"2023-01-01","dateModified":"2022-06-01"}</script>')
        r = ca.audit(html("<h1>x</h1>" + long_para(), head=head), as_of=dt.date(2026, 9, 25))
        self.assertTrue(has(r, "eeat", "medium", "months ago"))
        self.assertTrue(has(r, "eeat", "medium", "earlier than datePublished"))
        r = ca.audit(html("<h1>x</h1>" + long_para()))
        self.assertTrue(has(r, "eeat", "medium", "publish date"))

    def test_unsourced_stats_and_first_hand(self):
        body = "<h1>x</h1><p>About 70% fail and 40% relapse within a year.</p>" + long_para(420)
        r = ca.audit(html(body))
        self.assertTrue(has(r, "eeat", "medium", "no outbound source"))
        self.assertTrue(has(r, "eeat", "medium", "No first-hand"))
        r = ca.audit(html(body + '<p>Per <a href="https://data.example/s">the survey</a>, '
                                 'we tested 12 finishes.</p>'))
        self.assertFalse(has(r, "eeat", "medium", "no outbound source"))
        self.assertTrue(has(r, "eeat", "info", "first-hand"))

    def test_trust_links(self):
        r = ca.audit("<html><body><h1>x</h1>" + long_para() + "</body></html>")
        self.assertTrue(has(r, "eeat", "medium", "About or Contact"))


class StructureReadabilityDepthTest(unittest.TestCase):
    def test_headings(self):
        r = ca.audit(html(long_para()))
        self.assertTrue(has(r, "structure", "high", "No H1"))
        r = ca.audit(html("<h1>a</h1><h1>b</h1><h2>c?</h2><h4>d</h4>" + long_para()))
        self.assertTrue(has(r, "structure", "medium", "2 H1"))
        self.assertTrue(has(r, "structure", "medium", "skip"))
        self.assertTrue(has(r, "structure", "info", "1 phrased as questions"))
        r = ca.audit(html("<h1>a</h1>" + long_para(700)))
        self.assertTrue(has(r, "structure", "medium", "no H2"))

    def test_readability(self):
        run_on = ("<p>" + ("This sentence keeps going and going with clause after clause "
                           "and never really stops to let the reader breathe at all because "
                           "it wants to say everything at once without any pause whatsoever. ") * 6 + "</p>")
        r = ca.audit(html("<h1>a</h1>" + run_on))
        self.assertTrue(has(r, "readability", "medium", "Mean sentence length"))
        self.assertTrue(has(r, "readability", "medium", "exceed 30 words"))
        self.assertTrue(has(r, "readability", "medium", "over 150 words"))
        self.assertIsNotNone(ca.flesch("A short clear sentence. Another one here."))

    def test_depth_by_type(self):
        short = html("<h1>a</h1><p>" + "word " * 200 + "</p>")
        self.assertTrue(has(ca.audit(short), "depth", "high", "thin for an article"))
        self.assertFalse(has(ca.audit(short, page_type="product"), "depth", "high", "thin"))


class KeywordLinksOriginalityTest(unittest.TestCase):
    def test_keyword_placement_and_stuffing(self):
        r = ca.audit(html("<h1>Garden seating</h1>" + long_para()), keyword="teak chair")
        self.assertTrue(has(r, "keyword", "high", "missing from title and h1"))
        stuffed = "<h1>cedar bench</h1><p>" + "cedar bench " * 40 + "</p>"
        r = ca.audit(html(stuffed, title="cedar bench"), keyword="cedar bench")
        self.assertTrue(has(r, "keyword", "medium", "stuffing"))

    def test_links(self):
        r = ca.audit(html("<h1>a</h1>" + long_para(300)), url="https://e.test/p")
        self.assertTrue(has(r, "links", "high", "No in-content internal links"))
        body = "<h1>a</h1>" + long_para(300) + '<p><a href="/guide">click here</a></p>'
        r = ca.audit(html(body), url="https://e.test/p")
        self.assertTrue(has(r, "links", "medium", "generic anchor"))
        self.assertFalse(has(r, "links", "high", "No in-content"))

    def test_nav_links_do_not_count_as_in_content(self):
        body = "<nav><a href='/a'>A</a></nav><h1>a</h1>" + long_para(300)
        self.assertTrue(has(ca.audit(html(body)), "links", "high", "No in-content"))

    def test_originality(self):
        r = ca.audit(html("<h1>a</h1><p>We serve {{ city_name }} and nearby.</p>" + long_para()))
        self.assertTrue(has(r, "originality", "critical", "placeholder"))
        filler = ("<p>In today's fast-paced world it's important to note that we delve into "
                  "the ever-evolving landscape. Look no further, this game-changer will "
                  "unlock the power of rest.</p>")
        self.assertTrue(has(ca.audit(html("<h1>a</h1>" + filler + long_para())),
                            "originality", "high", "filler"))
        dup = "<p>The bench is sanded twice by hand before oiling.</p>" * 2
        self.assertTrue(has(ca.audit(html("<h1>a</h1>" + dup + long_para())),
                            "originality", "medium", "duplicated sentence"))


class FormatsGoldenCliTest(unittest.TestCase):
    def test_markdown_with_inline_html_is_markdown(self):
        md = "# Title\n\n<p align='center'><img src='x.png'></p>\n\nSome body text here.\n\n## Part\n\n[link](/a)\n"
        r = ca.audit(md)
        self.assertEqual(r["kind"], "markdown")
        self.assertEqual(r["title"], "Title")

    def test_golden(self):
        r = subprocess.run([sys.executable, SCRIPT, "--file", GOLDEN, "--url",
                            "https://example.test/blog/sleep-and-recovery", "--keyword",
                            "sleep and recovery", "--as-of", "2026-09-25"],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0)
        d = json.loads(r.stdout)
        self.assertTrue(d["ymyl"])
        self.assertEqual(d["score"], 13)
        self.assertEqual(d["dimensions"]["originality"]["critical"], 1)
        self.assertEqual(set(d["dimensions"]), set(ca.DIMENSIONS))

    def test_deterministic(self):
        raw = open(GOLDEN, encoding="utf-8").read()
        self.assertEqual(ca.audit(raw), ca.audit(raw))

    def test_bad_input(self):
        for args in (["--file", "/nope.html"], ["--url", "https://e.test", "--no-network"],
                     ["--file", GOLDEN, "--as-of", "yesterday"]):
            r = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True,
                               encoding="utf-8")
            self.assertEqual(r.returncode, 1, args)
            self.assertIn("error", json.loads(r.stdout))


if __name__ == "__main__":
    unittest.main()
