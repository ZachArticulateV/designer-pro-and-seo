#!/usr/bin/env python3
"""
image_audit.py — image SEO + performance audit for one page.

Inventories every <img> (and <picture>/<source>) and reports, per finding type with
the affected images listed:

  alt          missing alt, empty alt on a linked image (the link loses its name),
               filename-as-alt, "image of…" redundancy, over-long or keyword-stuffed
               alt, one alt reused across different images
  format       legacy JPEG/PNG/GIF/BMP/TIFF with no WebP/AVIF alternative
  responsive   content images without srcset / <picture>; w-descriptor srcset
               without sizes (the browser assumes 100vw)
  loading      lazy-loaded first image (likely LCP), several fetchpriority=high,
               no fetchpriority=high hint, many images with none lazy-loaded
  cls          no width+height and no CSS aspect-ratio
  size         (with --assets DIR) bytes over budget, intrinsic pixels far larger
               than the declared width, declared aspect ratio != intrinsic
  filename     camera / hash / generic file names
  social       og:image missing or relative

With --assets the script reads real file bytes and intrinsic dimensions from the image
headers (PNG, GIF, JPEG, WebP, AVIF — pure stdlib parsing). Without it, size checks are
listed under `needs_data` instead of guessed. Ready-to-run WebP/AVIF conversion
commands are emitted as text; the script never converts or writes images.

Each finding: {code, dimension, severity, finding, images, count, fix}; a deterministic
0-100 score (100 − 25/critical − 10/high − 4/medium per finding type).

Usage:
  python3 image_audit.py --file page.html [--url https://site/page] [--assets dist/] [--human]
  python3 image_audit.py --url https://site/page        # SSRF-guarded fetch

Standard library only.
"""
import argparse
import json
import os
import re
import struct
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import safe_open, UrlValidationError, SafeFetchError  # noqa: E402

UA = "Mozilla/5.0 (compatible; designer-pro-seo-images/1.0)"
PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}
LEGACY = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff")
MODERN_TYPES = ("image/webp", "image/avif")
HERO_BYTES, MAX_BYTES = 200 * 1024, 500 * 1024
BAD_NAME = re.compile(r"^(img|image|dsc|dscn|photo|pic|screenshot|screen shot|untitled|"
                      r"pxl|mvimg|whatsapp image)[-_ ]?\d*|^[0-9a-f]{16,}$|^\d{6,}$", re.I)
REDUNDANT = re.compile(r"^(an? )?(image|picture|photo|graphic|img) (of|showing)\b", re.I)


class _Imgs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs, self.og, self._pic, self._a = [], {}, None, 0
        self._a_text = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "picture":
            self._pic = {"types": set()}
        elif tag == "source" and self._pic is not None:
            t = a.get("type", "").lower()
            ss = a.get("srcset", "").lower()
            if t:
                self._pic["types"].add(t)
            for ext, mt in ((".webp", "image/webp"), (".avif", "image/avif")):
                if ext in ss:
                    self._pic["types"].add(mt)
        elif tag == "a":
            self._a += 1
            self._a_text = []
        elif tag == "img":
            a["_picture"] = sorted(self._pic["types"]) if self._pic is not None else None
            a["_in_link"] = self._a > 0
            a["_index"] = len(self.imgs)
            self.imgs.append(a)
        elif tag == "meta":
            k = (a.get("property") or a.get("name") or "").lower()
            if k in ("og:image", "twitter:image"):
                self.og.setdefault(k, a.get("content", ""))

    def handle_endtag(self, tag):
        if tag == "picture":
            self._pic = None
        elif tag == "a" and self._a:
            text = " ".join("".join(self._a_text).split())
            for i in reversed(self.imgs):
                if i.get("_in_link") and "_link_text" not in i:
                    i["_link_text"] = text
                else:
                    break
            self._a -= 1

    def handle_data(self, data):
        if self._a:
            self._a_text.append(data)


# --- intrinsic dimensions from file headers (stdlib only) ---------------------------------

def image_info(path):
    """(width, height, format) from the file header, or (None, None, None)."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(65536)
    except OSError:
        return None, None, None
    try:
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", head[16:24])
            return w, h, "png"
        if head[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", head[6:10])
            return w, h, "gif"
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            chunk = head[12:16]
            if chunk == b"VP8X":
                w = 1 + int.from_bytes(head[24:27], "little")
                h = 1 + int.from_bytes(head[27:30], "little")
            elif chunk == b"VP8L":
                b = int.from_bytes(head[21:25], "little")
                w, h = (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
            else:
                w, h = struct.unpack("<HH", head[26:30])
                w, h = w & 0x3FFF, h & 0x3FFF
            return w, h, "webp"
        if head[4:12] in (b"ftypavif", b"ftypavis"):
            i = head.find(b"ispe")
            if i > 0:
                w, h = struct.unpack(">II", head[i + 8:i + 16])
                return w, h, "avif"
            return None, None, "avif"
        if head[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(head):
                if head[i] != 0xFF:
                    i += 1
                    continue
                marker = head[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB,
                              0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", head[i + 5:i + 9])
                    return w, h, "jpeg"
                seg = struct.unpack(">H", head[i + 2:i + 4])[0]
                i += 2 + seg
            return None, None, "jpeg"
    except (struct.error, IndexError):
        pass
    return None, None, None


def _asset_path(src, assets, page_url):
    p = urlparse(src)
    if p.scheme in ("http", "https"):
        if page_url and p.netloc != urlparse(page_url).netloc:
            return None
        src = p.path
    if src.startswith("data:"):
        return None
    rel = unquote(src.split("?", 1)[0]).lstrip("/")
    path = os.path.normpath(os.path.join(assets, rel))
    if not path.startswith(os.path.normpath(assets)):     # no traversal out of --assets
        return None
    return path if os.path.isfile(path) else None


def _num(v):
    m = re.match(r"^\s*(\d+)", v or "")
    return int(m.group(1)) if m else None


# --- the audit ---------------------------------------------------------------------------

def audit(html, url=None, assets=None):
    p = _Imgs()
    p.feed(html)
    p.close()
    found = {}

    def hit(code, dim, sev, finding, img, fix):
        f = found.setdefault(code, {"code": code, "dimension": dim, "severity": sev,
                                    "finding": finding, "images": [], "fix": fix})
        src = img.get("src") or img.get("srcset", "").split(" ")[0] or "(no src)"
        if src not in f["images"]:
            f["images"].append(src)

    imgs = [i for i in p.imgs if i.get("src") or i.get("srcset")]
    content = [i for i in imgs if not (i.get("src", "").lower().endswith(".svg")
                                       or (_num(i.get("width")) or 999) < 64)]
    alts = {}
    for i in imgs:
        src = i.get("src", "")
        name = os.path.splitext(os.path.basename(urlparse(src).path))[0]
        decorative = i.get("role") == "presentation" or i.get("aria-hidden") == "true"
        if "alt" not in i:
            if decorative:
                hit("A2", "alt", "medium", "decorative image without alt=\"\"", i,
                    'Add alt="" so screen readers skip it.')
            else:
                hit("A1", "alt", "high", "image(s) missing alt", i,
                    "Describe what the image shows in context (or alt=\"\" if purely decorative).")
        else:
            alt = i["alt"].strip()
            if not alt and i.get("_in_link") and not i.get("_link_text"):
                hit("A3", "alt", "high", "linked image with empty alt (the link has no name)", i,
                    "Give the image an alt describing the link destination.")
            elif alt:
                low = alt.lower()
                if name and (low == name.lower() or re.sub(r"[-_]", " ", name.lower()) == low
                             or re.match(r"^[\w-]+\.(jpe?g|png|gif|webp|avif|svg)$", low)):
                    hit("A4", "alt", "medium", "alt text is just the file name", i,
                        "Write a human description, not the file name.")
                if REDUNDANT.match(alt):
                    hit("A5", "alt", "info", 'alt starts with "image of…" (redundant)', i,
                        "Drop the lead-in; screen readers already announce an image.")
                if len(alt) > 125:
                    hit("A6", "alt", "medium", "alt text over 125 characters", i,
                        "Keep alt concise; move long explanations to a caption.")
                words = re.findall(r"[a-z]+", low)
                if (alt.count(",") >= 3 and len(alt) < 150) or (
                        words and max(words.count(w) for w in set(words)) >= 3):
                    hit("A7", "alt", "medium", "alt looks keyword-stuffed", i,
                        "Describe the image naturally; one mention of the topic at most.")
                alts.setdefault(low, set()).add(src)
        if name and BAD_NAME.search(name):
            hit("N1", "filename", "info", "non-descriptive file name", i,
                "Name files by content (e.g. cedar-garden-bench.webp) before upload.")
    for alt, srcs in alts.items():
        if len(srcs) > 1:
            for s in srcs:
                hit("A8", "alt", "medium", "same alt text on different images",
                    {"src": s}, "Write alt text specific to each image.")

    for i in content:
        src = i.get("src", "").lower().split("?", 1)[0]
        srcset = i.get("srcset", "").lower()
        pic = i.get("_picture") or []
        modern = any(t in pic for t in MODERN_TYPES) or ".webp" in srcset or ".avif" in srcset \
            or src.endswith((".webp", ".avif"))
        if src.endswith(LEGACY) and not modern:
            hit("F1", "format", "medium", "legacy-format image(s) with no WebP/AVIF version", i,
                "Serve AVIF/WebP (via <picture> or the CDN); see `conversions`.")
        if not srcset and i.get("_picture") is None:
            hit("R1", "responsive", "medium", "content image(s) without srcset / <picture>", i,
                "Provide 2-4 widths via srcset + sizes so phones don't download desktop pixels.")
        elif re.search(r"\d+w\b", srcset) and not i.get("sizes"):
            hit("R2", "responsive", "medium", "srcset with w-descriptors but no sizes", i,
                "Add sizes (e.g. '(max-width: 600px) 100vw, 50vw'); default is 100vw.")
        if not (i.get("width") and i.get("height")) and "aspect-ratio" not in i.get("style", "").lower():
            hit("C1", "cls", "medium", "image(s) without width+height or aspect-ratio (CLS)", i,
                "Declare width and height attributes (or CSS aspect-ratio) to reserve space.")

    if content:
        first = content[0]
        if first.get("loading", "").lower() == "lazy":
            hit("L1", "loading", "high", "first content image (likely LCP) is lazy-loaded", first,
                "Remove loading=lazy from the hero and add fetchpriority=\"high\".")
        pri = [i for i in content if i.get("fetchpriority", "").lower() == "high"]
        if len(pri) > 1:
            for i in pri:
                hit("L2", "loading", "medium", "several images marked fetchpriority=high", i,
                    "Reserve fetchpriority=high for the single LCP image.")
        elif not pri:
            hit("L3", "loading", "info", "no image carries fetchpriority=high", first,
                "Mark the LCP image fetchpriority=\"high\".")
        rest = content[2:]
        if len(rest) >= 3 and not any(i.get("loading", "").lower() == "lazy" for i in rest):
            for i in rest:
                hit("L4", "loading", "medium", "below-the-fold images not lazy-loaded", i,
                    'Add loading="lazy" to images outside the first viewport.')

    # size checks need real bytes / pixels
    needs = []
    if assets:
        for i in content:
            path = _asset_path(i.get("src", ""), assets, url)
            if not path:
                continue
            nbytes = os.path.getsize(path)
            iw, ih, fmt = image_info(path)
            budget = HERO_BYTES if i is content[0] else MAX_BYTES // 2
            if nbytes > MAX_BYTES:
                hit("S1", "size", "high", f"image(s) over {MAX_BYTES // 1024} KB", i,
                    "Compress and resize; target under ~150 KB for most content images.")
            elif nbytes > budget:
                hit("S2", "size", "medium", "image(s) over the byte budget (200 KB hero / 250 KB other)",
                    i, "Re-encode as AVIF/WebP at quality ~60-80 and resize to display size.")
            dw, dh = _num(i.get("width")), _num(i.get("height"))
            if iw and dw and iw > 2.5 * dw and not i.get("srcset"):
                hit("S3", "size", "medium", "intrinsic pixels far larger than the declared width",
                    i, f"Resize toward {dw * 2}px wide (2x density) or add srcset.")
            if iw and ih and dw and dh:
                if abs(iw / ih - dw / dh) / (iw / ih) > 0.05:
                    hit("S4", "size", "medium", "declared aspect ratio differs from the file",
                        i, "Match width/height to the file's ratio to avoid distortion.")
    else:
        needs.append("file bytes + intrinsic dimensions (pass --assets BUILD_DIR, or fetch the "
                     "images) for size / oversize / aspect checks")

    og = p.og.get("og:image")
    if not og:
        found["O1"] = {"code": "O1", "dimension": "social", "severity": "medium",
                       "finding": "no og:image", "images": [],
                       "fix": "Add a 1200x630 og:image so shares and AI surfaces show a preview."}
    elif not urlparse(og).scheme:
        found["O2"] = {"code": "O2", "dimension": "social", "severity": "medium",
                       "finding": "og:image is not an absolute URL", "images": [og],
                       "fix": "Use an absolute https:// URL for og:image."}

    conversions = []
    for src in (found.get("F1") or {}).get("images", []):
        base, _ext = os.path.splitext(src.split("?", 1)[0])
        conversions.append({"src": src, "commands": [
            f"cwebp -q 78 '{src}' -o '{base}.webp'",
            f"avifenc --min 20 --max 32 '{src}' '{base}.avif'",
            f"magick '{src}' -quality 78 '{base}.webp'"]})

    order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    findings = sorted(found.values(), key=lambda f: (order[f["severity"]], f["code"]))
    for f in findings:
        f["count"] = len(f["images"])
    return {"action": "image-audit", "images": len(imgs), "content_images": len(content),
            "findings": findings, "conversions": conversions, "needs_data": needs,
            "score": max(0, 100 - sum(PENALTY[f["severity"]] for f in findings)),
            "note": "CSS background images and images injected by JavaScript are not seen "
                    "by an HTML parse; audit them in the rendered page."}


def _fetch(url):
    try:
        resp, _ = safe_open(url, timeout=10, headers={"User-Agent": UA})
    except (UrlValidationError, SafeFetchError, OSError, ValueError) as e:
        return None, str(e)
    try:
        return resp.read(4_000_000).decode("utf-8", "replace"), None
    finally:
        resp.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="image SEO audit")
    ap.add_argument("--file", help="local HTML file")
    ap.add_argument("--url", help="page URL (fetched when no --file; context otherwise)")
    ap.add_argument("--assets", help="build directory the image srcs resolve against")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)
    if a.file:
        try:
            with open(a.file, encoding="utf-8", errors="replace") as fh:
                html = fh.read()
        except OSError as e:
            print(json.dumps({"error": f"could not read {a.file}: {e}"}))
            return 1
    elif a.url and not a.no_network:
        html, err = _fetch(a.url)
        if html is None:
            print(json.dumps({"error": err}))
            return 1
    else:
        print(json.dumps({"error": "provide --file, or --url without --no-network"}))
        return 1
    if a.assets and not os.path.isdir(a.assets):
        print(json.dumps({"error": f"--assets {a.assets} is not a directory"}))
        return 1
    r = audit(html, a.url, a.assets)
    if a.human:
        print(f"# Image audit: {a.file or a.url}  {r['images']} images "
              f"({r['content_images']} content)  score {r['score']}/100")
        for f in r["findings"]:
            print(f"[{f['severity'].upper()}] {f['code']} ({f['dimension']}) {f['finding']}"
                  + (f" x{f['count']}" if f["count"] else ""))
            for s in f["images"][:4]:
                print(f"    - {s}")
            if f["severity"] != "info":
                print(f"    fix: {f['fix']}")
        for n in r["needs_data"]:
            print(f"[NEEDS DATA] {n}")
        if r["conversions"]:
            print("Conversions (run where cwebp / avifenc / ImageMagick are installed):")
            for c in r["conversions"]:
                print(f"    {c['commands'][0]}")
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
