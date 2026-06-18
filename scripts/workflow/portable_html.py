#!/usr/bin/env python3
"""
portable_html.py — Inline a multi-file HTML build into one portable file.

Inlines local <link rel=stylesheet> and <script src>, base64-embeds small local
images, strips dev artifacts (source maps), and reports size + platform warnings
so the result drops into any custom-HTML surface (WordPress, GoHighLevel, Webflow,
Wix, Framer, Squarespace, Carrd, ...).

Security: only inlines files INSIDE the source build directory. Absolute paths and
`..` traversal are refused and reported (prevents exfiltrating e.g. ../secret.env
into the output). Remote (http/https//) assets are left untouched.

Known limitations (reported, not silently ignored): does not rewrite CSS url(...),
@font-face, <img srcset>, <source>, or <link rel=icon>; those are listed so you can
handle them (usually CDN-host them). Standard library only.

Usage:
  python3 portable_html.py --in site/index.html --out portable.html \\
      [--target wordpress|ghl|webflow|wix|framer|squarespace|generic] \\
      [--inline-img-kb 50] [--human]
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys

PLATFORM_LIMITS = {
    "wordpress": ("WordPress (Gutenberg/Elementor Custom HTML)", None,
                  "Paste into a Custom HTML block (Gutenberg) or HTML widget (Elementor). Supports <style> and <script>."),
    "ghl": ("GoHighLevel Custom Code element", 5_000_000,
            "Paste into a Custom Code element in the funnel/page builder. Watch per-element size; host large media on a CDN."),
    "webflow": ("Webflow custom code embed", 50_000,
                "Webflow embeds cap inline code near 50KB — prefer external/CDN assets; this file may exceed it if images are inlined."),
    "wix": ("Wix HTML iframe (Embed a Widget)", None,
            "Runs in an isolated iframe; JS cannot reach the parent page. Self-contained files work well."),
    "framer": ("Framer code embed", None,
               "Full HTML+CSS+JS embed support."),
    "squarespace": ("Squarespace Code Block", None,
                    "Supports HTML+CSS+JS in a Code Block."),
    "carrd": ("Carrd Embed element (Code, Pro plan)", None,
              "Paste into an Embed element set to Code. The Embed element requires a Carrd Pro plan; keep the snippet self-contained."),
    "generic": ("Generic custom-HTML surface", None,
                "Any surface that accepts pasted HTML with <style>/<script>."),
}


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _is_remote(url):
    return url.startswith(("http://", "https://", "//", "data:", "mailto:", "tel:", "#"))


def safe_local_path(base_real, url):
    """Classify a URL relative to the build dir.

    Returns (status, value):
      REMOTE  -> leave untouched
      UNSAFE  -> absolute path or escapes base dir; REFUSE (security)
      MISSING -> inside base dir but file not found
      OK      -> (status, absolute_path) safe to inline
    """
    if _is_remote(url):
        return ("REMOTE", url)
    raw = url.split("?")[0].split("#")[0]
    if not raw:
        return ("REMOTE", url)
    # reject absolute (posix or windows) paths outright
    if os.path.isabs(raw) or raw.startswith(("\\", "/")) or re.match(r"^[A-Za-z]:", raw):
        return ("UNSAFE", raw)
    resolved = os.path.realpath(os.path.join(base_real, raw))
    try:
        if os.path.commonpath([resolved, base_real]) != base_real:
            return ("UNSAFE", raw)
    except ValueError:  # different drives on Windows
        return ("UNSAFE", raw)
    if not os.path.exists(resolved):
        return ("MISSING", raw)
    return ("OK", resolved)


def inline_css(html, base_real, warnings, external):
    pattern = re.compile(r'<link[^>]*rel=["\']?stylesheet["\']?[^>]*>', re.I)

    def repl(m):
        tag = m.group(0)
        href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
        if not href:
            return tag
        status, val = safe_local_path(base_real, href.group(1))
        if status == "REMOTE":
            external.append(f"remote CSS: {href.group(1)}")
            return tag
        if status == "UNSAFE":
            warnings.append(f"REFUSED unsafe CSS path (left as link): {val}")
            return tag
        if status == "MISSING":
            warnings.append(f"CSS not found, left as link: {val}")
            return tag
        return f"<style>\n{_read(val)}\n</style>"

    return pattern.sub(repl, html)


def inline_js(html, base_real, warnings, external):
    pattern = re.compile(r'<script([^>]*)\ssrc=["\']([^"\']+)["\']([^>]*)>\s*</script>', re.I)

    def repl(m):
        before, url, after = m.group(1), m.group(2), m.group(3)
        attrs = before + after
        status, val = safe_local_path(base_real, url)
        if status == "REMOTE":
            external.append(f"remote JS: {url}")
            return m.group(0)
        if status == "UNSAFE":
            warnings.append(f"REFUSED unsafe JS path (left as src): {val}")
            return m.group(0)
        if status == "MISSING":
            warnings.append(f"JS not found, left as src: {url}")
            return m.group(0)
        js = re.sub(r'//[#@]\s*sourceMappingURL=.*', '', _read(val))
        typ = ' type="module"' if re.search(r'type=["\']module["\']', attrs, re.I) else ''
        if re.search(r'\b(async|defer|nomodule)\b', attrs, re.I):
            warnings.append(f"inlined {url}: async/defer/nomodule no longer apply (inline scripts run synchronously)")
        return f"<script{typ}>\n{js}\n</script>"

    return pattern.sub(repl, html)


def inline_images(html, base_real, max_bytes, warnings, external):
    pattern = re.compile(r'<img[^>]*\ssrc=["\']([^"\']+)["\'][^>]*>', re.I)

    def repl(m):
        tag, url = m.group(0), m.group(1)
        status, val = safe_local_path(base_real, url)
        if status == "REMOTE":
            external.append(f"remote image: {url}")
            return tag
        if status == "UNSAFE":
            warnings.append(f"REFUSED unsafe image path (left as src): {val}")
            return tag
        if status == "MISSING":
            warnings.append(f"Image not found, left as src: {url}")
            return tag
        size = os.path.getsize(val)
        if size > max_bytes:
            external.append(f"large image left external ({size//1024}KB): {url}")
            warnings.append(f"Image {url} is {size//1024}KB (> {max_bytes//1024}KB) — left external; host on a CDN.")
            return tag
        mime = mimetypes.guess_type(val)[0] or "image/png"
        with open(val, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return tag.replace(url, f"data:{mime};base64,{b64}")

    return pattern.sub(repl, html)


def scan_unhandled(html, warnings):
    """Honestly report references this basic inliner does NOT rewrite."""
    checks = [
        (r'url\(\s*["\']?(?!data:|https?:|//|#)', "CSS url(...) references (fonts/bg images) are not inlined"),
        (r'\bsrcset=', "<img srcset> / responsive sources are not inlined"),
        (r'<source\b', "<source> elements (picture/video/audio) are not inlined"),
        (r'<link[^>]*rel=["\'](?:icon|apple-touch-icon|manifest)', "favicon/manifest links are not inlined"),
    ]
    for pat, msg in checks:
        if re.search(pat, html, re.I):
            warnings.append(msg + " — host these on a CDN or use absolute URLs.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", required=True)
    ap.add_argument("--target", default="generic", choices=list(PLATFORM_LIMITS))
    ap.add_argument("--inline-img-kb", type=int, default=50)
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.infile):
        print(f"ERROR: input not found: {args.infile}", file=sys.stderr)
        sys.exit(1)

    base_real = os.path.realpath(os.path.dirname(os.path.abspath(args.infile)))
    html = _read(args.infile)
    warnings, external = [], []

    html = inline_css(html, base_real, warnings, external)
    html = inline_js(html, base_real, warnings, external)
    html = inline_images(html, base_real, args.inline_img_kb * 1024, warnings, external)
    scan_unhandled(html, warnings)

    with open(args.outfile, "w", encoding="utf-8") as f:
        f.write(html)

    out_bytes = os.path.getsize(args.outfile)
    label, limit, instructions = PLATFORM_LIMITS[args.target]
    if limit and out_bytes > limit:
        warnings.append(f"Output is {out_bytes//1024}KB, over {label} limit (~{limit//1024}KB). Externalize images/JS to a CDN.")

    report = {
        "input": args.infile,
        "output": args.outfile,
        "output_kb": round(out_bytes / 1024, 1),
        "target": args.target,
        "target_label": label,
        "paste_instructions": instructions,
        "warnings": warnings,
        "remaining_external_assets": external,
    }

    if args.human:
        print(f"Portable HTML written: {args.outfile} ({report['output_kb']} KB)")
        print(f"Target: {label}")
        print(f"How to paste: {instructions}")
        if external:
            print("\nLeft external (handle separately):")
            for e in external:
                print(f"  - {e}")
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f"  ! {w}")
        if not warnings and not external:
            print("\nFully self-contained — no warnings.")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
