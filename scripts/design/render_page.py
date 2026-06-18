#!/usr/bin/env python3
"""
render_page.py — Render a real, on-brand, accessible single-file HTML landing page
FROM a design-system spec produced by design_system.py.

This is the bridge from "we have a design system" to "we have a page": it turns the
engine's palette / typography / effects / key_sections into a semantic, responsive,
WCAG-aware HTML scaffold you can fill with copy and then run through
portable-html-port. Buttons use the palette's contrast-safe `on_primary`; motion
ships with a prefers-reduced-motion fallback; focus-visible states are included.

Standard library only. Deterministic.

Usage:
  # straight from the engine:
  python3 render_page.py --product-type saas-landing --industry saas \\
      --keywords "modern, trustworthy" --out page.html
  # or from a saved engine JSON:
  python3 design_system.py --product-type saas-landing --industry saas > ds.json
  python3 render_page.py --design-json ds.json --out page.html
"""
import argparse
import json
import os
import subprocess
import sys
from html import escape as _esc

SECTION_LABELS = {
    "hero": "Hero", "value": "Value", "social-proof": "Social proof",
    "features": "Features", "pricing": "Pricing", "faq": "FAQ", "cta": "Call to action",
    "menu": "Menu", "services": "Services", "reviews": "Reviews", "gallery": "Gallery",
    "about": "About", "contact": "Contact", "story": "Story", "collection": "Collection",
}


def run_engine(product_type, industry, keywords):
    here = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, os.path.join(here, "design_system.py"),
           "--product-type", product_type, "--industry", industry, "--keywords", keywords]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "engine failed")
    return json.loads(out.stdout)


def _font_link(d):
    t = d.get("typography") or {}
    fams = []
    for key in ("heading_font", "body_font"):
        fam = t.get(key)
        if fam and fam not in fams:
            fams.append(fam)
    if not fams:
        return ""
    spec = "&".join(f"family={f.replace(' ', '+')}:wght@400;600;700" for f in fams)
    return f'<link rel="preconnect" href="https://fonts.googleapis.com">\n' \
           f'  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?{spec}&display=swap">'


def _section_id(sec):
    """Slug used consistently for both a section's id and its nav anchor href."""
    return _esc(sec.replace(" ", "-"), quote=True)


def _section_html(sec):
    label = _esc(SECTION_LABELS.get(sec, sec.replace("-", " ").title()), quote=False)
    sid = _section_id(sec)
    if sec == "hero":
        return ""  # hero rendered separately
    if sec in ("cta",):
        return (f'  <section id="{sid}" class="band">\n'
                f'    <h2>{label}: your closing line goes here</h2>\n'
                f'    <a class="btn" href="#hero">Primary action</a>\n  </section>')
    if sec in ("features", "services", "collection"):
        cards = "\n".join(
            f'      <article class="card"><h3>{label} {i}</h3><p>One clear benefit, stated plainly.</p></article>'
            for i in (1, 2, 3))
        return (f'  <section id="{sid}" class="section reveal">\n    <h2>{label}</h2>\n'
                f'    <div class="grid">\n{cards}\n    </div>\n  </section>')
    return (f'  <section id="{sid}" class="section reveal">\n    <h2>{label}</h2>\n'
            f'    <p>Replace with your {label.lower()} content.</p>\n  </section>')


def render(d):
    pal = d.get("palette") or {}
    typ = d.get("typography") or {}
    eff = d.get("effects") or {}
    sections = d.get("key_sections") or ["hero", "features", "cta"]
    heading = typ.get("heading_font", "system-ui")
    body = typ.get("body_font", "system-ui")
    radius = eff.get("radius", "8px")
    # motion duration token like "200ms ease-out"
    motion = eff.get("motion", "200ms ease-out")

    def v(key, default):
        return pal.get(key) or default

    css = f""":root {{
  --primary: {v('primary', '#2c61dd')};
  --secondary: {v('secondary', '#6954d4')};
  --accent: {v('accent', '#ea832e')};
  --bg: {v('bg', '#ffffff')};
  --surface: {v('surface', '#f4f5f7')};
  --text: {v('text', '#1a1d24')};
  --on-primary: {v('on_primary', '#ffffff')};
  --radius: {radius};
  --motion: {motion};
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ margin: 0; background: var(--bg); color: var(--text);
  font-family: "{body}", system-ui, -apple-system, sans-serif; line-height: 1.6; }}
h1, h2, h3 {{ font-family: "{heading}", Georgia, serif; line-height: 1.15; }}
a {{ color: var(--primary); }}
.container {{ max-width: 1080px; margin: 0 auto; padding: 0 24px; }}
header.site {{ display: flex; justify-content: space-between; align-items: center;
  padding: 18px 24px; position: sticky; top: 0; background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(8px); z-index: 10; }}
header .brand {{ font-family: "{heading}", serif; font-weight: 700; }}
nav a {{ margin-left: 20px; text-decoration: none; color: var(--text); }}
.hero {{ padding: 14vh 24px 10vh; max-width: 760px; margin: 0 auto; text-align: center; }}
.hero h1 {{ font-size: clamp(2.2rem, 6vw, 4rem); margin: 0 0 .4em; }}
.hero p {{ font-size: 1.25rem; color: color-mix(in srgb, var(--text) 75%, transparent); }}
.btn {{ display: inline-block; background: var(--primary); color: var(--on-primary);
  text-decoration: none; padding: 14px 26px; border-radius: var(--radius); font-weight: 600;
  border: 0; cursor: pointer; transition: transform var(--motion), filter var(--motion); }}
.btn:hover {{ filter: brightness(1.05); transform: translateY(-1px); }}
.btn:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 3px; }}
.section {{ padding: 8vh 24px; max-width: 1080px; margin: 0 auto; }}
.section h2 {{ font-size: clamp(1.6rem, 4vw, 2.4rem); }}
.band {{ background: var(--surface); text-align: center; padding: 10vh 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-top: 28px; }}
.card {{ background: var(--surface); border-radius: var(--radius); padding: 24px; }}
footer {{ padding: 6vh 24px; text-align: center; color: color-mix(in srgb, var(--text) 60%, transparent); }}
.reveal {{ opacity: 0; transform: translateY(16px); transition: opacity var(--motion), transform var(--motion); }}
.reveal.in {{ opacity: 1; transform: none; }}
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; scroll-behavior: auto !important; }}
  .reveal {{ opacity: 1; transform: none; }}
}}"""

    nav_links = "\n".join(
        f'      <a href="#{_section_id(s)}">{_esc(SECTION_LABELS.get(s, s.title()), quote=False)}</a>'
        for s in sections if s != "hero")
    body_sections = "\n".join(_section_html(s) for s in sections if s != "hero")

    js = """<script>
  // Reveal-on-scroll (respects reduced-motion via CSS).
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const io = new IntersectionObserver((es) => {
      es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    document.querySelectorAll('.reveal').forEach(el => io.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
  }
</script>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(str(d.get('input', {}).get('product_type') or 'Landing page'), quote=False)} — replace with your title</title>
  <meta name="description" content="Replace with a 120-160 char meta description.">
  {_font_link(d)}
  <style>
{css}
  </style>
</head>
<body>
  <header class="site">
    <span class="brand">Your Brand</span>
    <nav>
{nav_links}
    </nav>
  </header>
  <main>
    <section id="hero" class="hero">
      <h1>The outcome your visitor wants, in one line.</h1>
      <p>One sentence that earns belief. Then the single action below.</p>
      <p><a class="btn" href="#cta">Primary action</a></p>
    </section>
{body_sections}
  </main>
  <footer>© Your Brand. Built from a designer-pro-and-seo design system.</footer>
  {js}
</body>
</html>
"""
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design-json", help="path to design_system.py JSON ('-' for stdin)")
    ap.add_argument("--product-type", default="")
    ap.add_argument("--industry", default="")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--out", default="page.html")
    args = ap.parse_args()

    try:
        if args.design_json:
            if args.design_json == "-":
                raw = sys.stdin.read()
            else:
                with open(args.design_json, encoding="utf-8") as fh:
                    raw = fh.read()
            d = json.loads(raw)
        elif args.product_type:
            d = run_engine(args.product_type, args.industry, args.keywords)
        else:
            print("Provide --design-json or --product-type.", file=sys.stderr)
            sys.exit(2)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": "could not read design JSON: %s" % e}))
        sys.exit(1)
    except RuntimeError as e:
        print(json.dumps({"error": "design engine failed: %s" % e}))
        sys.exit(1)

    try:
        page_html = render(d)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(page_html)
    except OSError as e:
        print(json.dumps({"error": "could not write --out %s: %s" % (args.out, e)}))
        sys.exit(1)
    fb = d.get("_fallbacks", [])
    print(json.dumps({
        "out": args.out, "bytes": os.path.getsize(args.out),
        "style": (d.get("style") or {}).get("name"),
        "palette": (d.get("palette") or {}).get("name"),
        "sections": d.get("key_sections"),
        "fallbacks": fb,
        "next": "Fill the copy, then run portable-html-port to drop it into any CMS.",
    }, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
