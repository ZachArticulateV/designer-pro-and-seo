"""image_audit.py (v1.7) -- image SEO audit: alt quality, format, responsive, loading,
CLS, byte/pixel budgets from real file headers, social image, conversions, golden.

Offline, stdlib-only; runs under unittest and pytest.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "seo", "image_audit.py")
EX = os.path.join(ROOT, "references", "examples", "seo-image-audit")
sys.path.insert(0, os.path.join(ROOT, "scripts", "seo"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
import image_audit as ia  # noqa: E402

OG = '<meta property="og:image" content="https://e.test/og.jpg">'


def page(body, head=OG):
    return "<html><head>%s</head><body>%s</body></html>" % (head, body)


def codes(r):
    return {f["code"] for f in r["findings"]}


def png_bytes(w, h):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x10\x20\x30" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class HeaderParseTest(unittest.TestCase):
    def _info(self, data):
        with tempfile.NamedTemporaryFile(delete=False) as fh:
            fh.write(data)
        try:
            return ia.image_info(fh.name)
        finally:
            os.unlink(fh.name)

    def test_formats(self):
        self.assertEqual(self._info(png_bytes(7, 3)), (7, 3, "png"))
        self.assertEqual(self._info(b"GIF89a" + struct.pack("<HH", 12, 9) + b"\x00" * 8),
                         (12, 9, "gif"))
        vp8x = (b"RIFF\x00\x00\x00\x00WEBPVP8X" + b"\x00" * 8
                + (299).to_bytes(3, "little") + (199).to_bytes(3, "little"))
        self.assertEqual(self._info(vp8x), (300, 200, "webp"))
        bits = (640 - 1) | ((480 - 1) << 14)
        vp8l = b"RIFF\x00\x00\x00\x00WEBPVP8L\x00\x00\x00\x00\x2f" + bits.to_bytes(4, "little")
        self.assertEqual(self._info(vp8l), (640, 480, "webp"))
        jpeg = (b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 16) + b"\x00" * 14
                + b"\xff\xc0" + struct.pack(">HBHH", 17, 8, 250, 400) + b"\x00" * 12)
        self.assertEqual(self._info(jpeg), (400, 250, "jpeg"))
        avif = (b"\x00\x00\x00\x1cftypavif" + b"\x00" * 20 + b"\x00\x00\x00\x14ispe"
                + b"\x00" * 4 + struct.pack(">II", 1024, 768))
        self.assertEqual(self._info(avif), (1024, 768, "avif"))
        self.assertEqual(self._info(b"not an image"), (None, None, None))


class AltTest(unittest.TestCase):
    def test_missing_and_decorative(self):
        r = ia.audit(page('<img src="/a.webp" width="1" height="1">'
                          '<img src="/b.webp" role="presentation" width="1" height="1">'))
        self.assertTrue({"A1", "A2"} <= codes(r))

    def test_linked_empty_alt_vs_linked_with_text(self):
        self.assertIn("A3", codes(ia.audit(page('<a href="/x"><img src="/a.webp" alt=""></a>'))))
        self.assertNotIn("A3", codes(ia.audit(page('<a href="/x"><img src="/a.webp" alt=""> Porch swing</a>'))))
        self.assertNotIn("A3", codes(ia.audit(page('<img src="/a.webp" alt="">'))))

    def test_quality_rules(self):
        r = ia.audit(page('<img src="/img/bench-01.webp" alt="bench-01">'
                          '<img src="/c.webp" alt="Image of a bench on a patio">'
                          '<img src="/d.webp" alt="%s">'
                          '<img src="/e.webp" alt="bench, cedar bench, bench sale, best bench">'
                          '<img src="/f.webp" alt="A bench"><img src="/g.webp" alt="a bench">'
                          % ("x" * 130)))
        self.assertTrue({"A4", "A5", "A6", "A7", "A8"} <= codes(r))


class FormatResponsiveLoadingTest(unittest.TestCase):
    def test_legacy_format_unless_modern_alternative(self):
        self.assertIn("F1", codes(ia.audit(page('<img src="/a.jpg" alt="a">'))))
        pic = ('<picture><source type="image/avif" srcset="/a.avif">'
               '<img src="/a.jpg" alt="a"></picture>')
        r = ia.audit(page(pic))
        self.assertNotIn("F1", codes(r))
        self.assertNotIn("R1", codes(r))
        self.assertNotIn("F1", codes(ia.audit(page('<img src="/a.jpg" srcset="/a-800.webp 800w" alt="a">'))))

    def test_srcset_without_sizes(self):
        r = ia.audit(page('<img src="/a.webp" srcset="/a-400.webp 400w, /a-800.webp 800w" alt="a">'))
        self.assertIn("R2", codes(r))

    def test_loading_rules(self):
        imgs = '<img src="/h.webp" alt="h" loading="lazy">' + "".join(
            '<img src="/%d.webp" alt="x%d">' % (i, i) for i in range(5))
        r = ia.audit(page(imgs))
        self.assertTrue({"L1", "L3", "L4"} <= codes(r))
        two = ('<img src="/a.webp" alt="a" fetchpriority="high">'
               '<img src="/b.webp" alt="b" fetchpriority="high">')
        self.assertIn("L2", codes(ia.audit(page(two))))

    def test_icons_and_svg_are_not_content_images(self):
        r = ia.audit(page('<img src="/logo.svg" alt="Logo"><img src="/i.png" alt="i" width="24" height="24">'))
        self.assertEqual(r["content_images"], 0)
        self.assertFalse({"R1", "F1", "C1"} & codes(r))

    def test_og_image(self):
        self.assertIn("O1", codes(ia.audit(page("", head=""))))
        self.assertIn("O2", codes(ia.audit(page("", head='<meta property="og:image" content="/og.jpg">'))))


class SizeTest(unittest.TestCase):
    def test_byte_budgets_and_traversal_guard(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "big.jpg"), "wb") as fh:
                fh.write(os.urandom(600 * 1024))
            with open(os.path.join(td, "mid.jpg"), "wb") as fh:
                fh.write(os.urandom(300 * 1024))
            html = page('<img src="/big.jpg" alt="a" width="800" height="600">'
                        '<img src="/mid.jpg" alt="b" width="800" height="600">'
                        '<img src="/../../etc/passwd" alt="c" width="800" height="600">')
            r = ia.audit(html, assets=td)
            self.assertTrue({"S1", "S2"} <= codes(r))
            self.assertEqual(r["needs_data"], [])
        self.assertTrue(ia.audit(page('<img src="/a.jpg" alt="a">'))["needs_data"])


class GoldenCliTest(unittest.TestCase):
    def test_golden(self):
        r = subprocess.run([sys.executable, SCRIPT, "--file", os.path.join(EX, "page.html"),
                            "--url", "https://example.test/benches/classic",
                            "--assets", os.path.join(EX, "assets")],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0)
        d = json.loads(r.stdout)
        self.assertEqual(d["score"], 48)
        self.assertEqual(codes(d), {"A3", "A4", "A7", "C1", "F1", "L1", "L3", "N1", "O1",
                                    "R1", "S3", "S4"})
        self.assertEqual(len(d["conversions"]), 4)

    def test_bad_input(self):
        for args in (["--file", "/nope.html"], ["--url", "https://e.test", "--no-network"],
                     ["--file", os.path.join(EX, "page.html"), "--assets", "/nope"]):
            r = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True,
                               encoding="utf-8")
            self.assertEqual(r.returncode, 1, args)


if __name__ == "__main__":
    unittest.main()
