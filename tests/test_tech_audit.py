"""tech_audit.py depth (v1.2) -- the 10-dimension technical audit.

Pins every new check with a minimal fixture (one signal per case), the structured
record shape the seo-technical agent fans in ({dimension, severity, finding, fix}),
the deterministic lab score, the golden example, and the corrected mixed-content
semantics (a plain <a href="http://"> link is NOT mixed content).

Offline, stdlib-only; runs under unittest and pytest.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "seo", "tech_audit.py")
GOLDEN = os.path.join(ROOT, "references", "examples", "seo-technical", "sample-page.html")
sys.path.insert(0, os.path.join(ROOT, "scripts", "seo"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
import tech_audit  # noqa: E402

HEAD = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<title>A perfectly reasonable page title</title>'
        '<meta name="description" content="%s">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<link rel="canonical" href="https://e.test/p">'
        '<meta property="og:title" content="t"><meta property="og:description" content="d">'
        '<meta property="og:image" content="https://e.test/i.png">'
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>'
        % ("x" * 130))
BODY_TEXT = "<p>" + " ".join(["word"] * 120) + "</p>"


def page(head_extra="", body="", head=HEAD):
    return head + head_extra + "</head><body><h1>Heading</h1>" + BODY_TEXT + body + "</body></html>"


def checks(html, url="https://e.test/p", headers=None):
    return tech_audit.analyze_html(html, url, headers)["checks"]


def has(cs, dim, sev, needle):
    return any(c["dimension"] == dim and c["severity"] == sev and needle in c["finding"]
               for c in cs)


class CleanPageTest(unittest.TestCase):
    def test_clean_page_has_no_actionable_findings(self):
        cs = checks(page())
        bad = [c for c in cs if c["severity"] != "info"]
        self.assertEqual(bad, [], bad)
        self.assertEqual(tech_audit.lab_score(cs), 100)

    def test_every_record_has_the_contract_shape(self):
        for c in checks(page(body='<img src="/a.jpg">')):
            self.assertEqual(set(c), {"dimension", "severity", "finding", "fix"})
            self.assertIn(c["dimension"], tech_audit.DIMENSIONS)
            self.assertIn(c["severity"], tech_audit.SEVERITIES)
            if c["severity"] != "info":
                self.assertTrue(c["fix"], c)


class IndexabilityTest(unittest.TestCase):
    def test_x_robots_tag_noindex_is_critical(self):
        cs = checks(page(), headers={"x-robots-tag": "noindex"})
        self.assertTrue(has(cs, "indexability", "critical", "X-Robots-Tag"))

    def test_noindex_plus_canonical_conflict(self):
        cs = checks(page('<meta name="robots" content="noindex">'))
        self.assertTrue(has(cs, "indexability", "critical", "NOINDEX"))
        self.assertTrue(has(cs, "indexability", "high", "mixed signals"))

    def test_nosnippet_flags_ai_overview_opt_out(self):
        cs = checks(page('<meta name="googlebot" content="nosnippet">'))
        self.assertTrue(has(cs, "indexability", "medium", "AI Overview"))

    def test_relative_multiple_and_cross_host_canonical(self):
        h = HEAD.replace('href="https://e.test/p"', 'href="/p"')
        self.assertTrue(has(checks(page(head=h)), "indexability", "medium", "relative"))
        cs = checks(page('<link rel="canonical" href="https://other.test/p">'))
        self.assertTrue(has(cs, "indexability", "high", "conflicting canonical"))
        h2 = HEAD.replace('https://e.test/p"', 'https://other.test/p"')
        self.assertTrue(has(checks(page(head=h2)), "indexability", "medium", "another host"))

    def test_two_mb_index_limit(self):
        big = page(body="<p>" + "a " * (1100 * 1024) + "</p>")
        self.assertTrue(has(checks(big), "indexability", "critical", "2 MB"))

    def test_missing_doctype_and_charset(self):
        h = HEAD.replace("<!DOCTYPE html>", "").replace('<meta charset="utf-8">', "")
        cs = checks(page(head=h))
        self.assertTrue(has(cs, "indexability", "medium", "DOCTYPE"))
        self.assertTrue(has(cs, "indexability", "medium", "encoding"))

    def test_hreflang_without_x_default(self):
        cs = checks(page('<link rel="alternate" hreflang="de" href="https://e.test/de/">'))
        self.assertTrue(has(cs, "indexability", "info", "without x-default"))


class CwvLabTest(unittest.TestCase):
    def test_lazy_first_image_is_high(self):
        cs = checks(page(body='<img src="/hero.jpg" alt="h" width="1" height="1" loading="lazy">'))
        self.assertTrue(has(cs, "cwv", "high", "loading=lazy"))

    def test_render_blocking_head_script(self):
        cs = checks(page('<script src="/a.js"></script><script src="/b.js" defer></script>'
                         '<script type="module" src="/c.js"></script>'))
        self.assertTrue(has(cs, "cwv", "medium", "1 render-blocking"))

    def test_images_without_dimensions_unless_aspect_ratio(self):
        cs = checks(page(body='<img src="/a.jpg" alt="a">'
                              '<img src="/b.jpg" alt="b" style="aspect-ratio:4/3">'))
        self.assertTrue(has(cs, "cwv", "medium", "1/2 <img> without width/height"))

    def test_large_inline_script(self):
        cs = checks(page('<script>window.__STATE__=%s</script>' % ('"x",' * 40000)))
        self.assertTrue(has(cs, "cwv", "medium", "Inline script"))


class RenderingSecurityMobileTest(unittest.TestCase):
    def test_spa_shell(self):
        html = HEAD + '<script src="/app.js"></script></head><body><div id="root"></div></body></html>'
        self.assertTrue(has(checks(html), "js-rendering", "high", "client-rendered shell"))

    def test_short_server_rendered_page_is_not_a_shell(self):
        html = page(body="").replace(BODY_TEXT, "<p>" + "w " * 40 + "</p>")
        html = html.replace("</head>", '<script src="/x.js" defer></script></head>')
        self.assertFalse(has(checks(html), "js-rendering", "high", "shell"))

    def test_js_only_links(self):
        cs = checks(page(body='<a onclick="go()">x</a><a href="javascript:void(0)">y</a>'))
        self.assertTrue(has(cs, "js-rendering", "medium", "2 <a> without a crawlable href"))

    def test_http_anchor_is_not_mixed_content(self):
        cs = checks(page(body='<a href="http://e.test/x">x</a>'))
        self.assertFalse(has(cs, "security", "high", "Mixed content"))
        self.assertTrue(has(cs, "security", "info", "http:// URLs"))

    def test_http_subresource_is_mixed_content(self):
        cs = checks(page(body='<img src="http://cdn.e.test/a.png" alt="a" width="1" height="1">'))
        self.assertTrue(has(cs, "security", "high", "Mixed content"))

    def test_zoom_disabled(self):
        h = HEAD.replace("initial-scale=1", "initial-scale=1, maximum-scale=1")
        self.assertTrue(has(checks(page(head=h)), "mobile", "medium", "pinch-zoom"))


class StructuredDataUrlTest(unittest.TestCase):
    def test_bad_json_ld_and_retired_type(self):
        cs = checks(page('<script type="application/ld+json">{bad</script>'
                         '<script type="application/ld+json">{"@type":"FAQPage"}</script>'))
        self.assertTrue(has(cs, "structured-data", "high", "do not parse"))
        self.assertTrue(has(cs, "structured-data", "info", "FAQPage"))

    def test_url_structure(self):
        self.assertTrue(has(checks(page(), "https://e.test/Blog_Post?a=1&b=2&c=3"),
                            "url-structure", "medium", "uppercase"))
        self.assertTrue(has(checks(page(), "https://e.test/p?sid=abc"),
                            "url-structure", "high", "Session id"))


class CliGoldenTest(unittest.TestCase):
    def _run(self, *args):
        r = subprocess.run([sys.executable, SCRIPT, *args, "--no-network"],
                           capture_output=True, encoding="utf-8")
        return r.returncode, r.stdout

    def test_golden_example_findings_and_score(self):
        rc, out = self._run("--file", GOLDEN, "--url", "https://example.test/benches")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        high = data["findings"]["high"]
        self.assertIn("Mixed content: http:// resources on the page", high)
        self.assertTrue(any("loading=lazy" in h for h in high))
        self.assertEqual(data["score"], 64)
        self.assertEqual(set(data["dimensions"]), set(tech_audit.DIMENSIONS))

    def test_deterministic(self):
        self.assertEqual(self._run("--file", GOLDEN), self._run("--file", GOLDEN))

    def test_missing_file_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            rc, out = self._run("--file", os.path.join(td, "nope.html"))
            self.assertEqual(rc, 1)
            self.assertTrue(json.loads(out)["errors"])


if __name__ == "__main__":
    unittest.main()
