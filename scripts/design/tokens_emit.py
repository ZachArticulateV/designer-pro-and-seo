#!/usr/bin/env python3
"""
tokens_emit.py — Emit code-deliverable design tokens from a design_system.py spec.

Turns the engine's palette / typography / effects into real token files your build
can import: CSS custom properties, a Tailwind config fragment, SCSS variables, or a
Style-Dictionary-style JSON. Closes the gap from "design system doc" to "tokens in
the codebase."

Standard library only. Deterministic.

Usage:
  python3 design_system.py --product-type saas-landing --industry saas > ds.json
  python3 tokens_emit.py --design-json ds.json --format css     # or tailwind|scss|json|all
"""
import argparse
import json
import os
import sys


def _tokens(d):
    pal = d.get("palette") or {}
    typ = d.get("typography") or {}
    eff = d.get("effects") or {}
    colors = {k: pal.get(k) for k in ("primary", "secondary", "accent", "bg", "surface",
                                      "text", "on_primary", "success", "warning", "error")
              if pal.get(k)}
    return {
        "colors": colors,
        "fonts": {"heading": typ.get("heading_font"), "body": typ.get("body_font")},
        "radius": eff.get("radius"),
        "motion": eff.get("motion"),
    }


def emit_css(t):
    lines = [":root {"]
    for k, v in t["colors"].items():
        lines.append(f"  --color-{k.replace('_', '-')}: {v};")
    if t["fonts"]["heading"]:
        lines.append(f'  --font-heading: "{t["fonts"]["heading"]}", serif;')
    if t["fonts"]["body"]:
        lines.append(f'  --font-body: "{t["fonts"]["body"]}", system-ui, sans-serif;')
    if t["radius"]:
        lines.append(f"  --radius: {t['radius']};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def emit_scss(t):
    lines = []
    for k, v in t["colors"].items():
        lines.append(f"$color-{k.replace('_', '-')}: {v};")
    if t["fonts"]["heading"]:
        lines.append(f'$font-heading: "{t["fonts"]["heading"]}", serif;')
    if t["fonts"]["body"]:
        lines.append(f'$font-body: "{t["fonts"]["body"]}", system-ui, sans-serif;')
    if t["radius"]:
        lines.append(f"$radius: {t['radius']};")
    return "\n".join(lines) + "\n"


def emit_tailwind(t):
    colors = ",\n".join(f'        "{k.replace("_", "-")}": "{v}"' for k, v in t["colors"].items())
    heading = t["fonts"]["heading"] or "ui-serif"
    body = t["fonts"]["body"] or "ui-sans-serif"
    radius = t["radius"] or "0.5rem"
    return f"""/** Tailwind token fragment — merge into tailwind.config.js `theme.extend` */
module.exports = {{
  theme: {{
    extend: {{
      colors: {{
{colors}
      }},
      fontFamily: {{
        heading: ['"{heading}"', 'serif'],
        body: ['"{body}"', 'system-ui', 'sans-serif']
      }},
      borderRadius: {{ DEFAULT: "{radius}" }}
    }}
  }}
}};
"""


def emit_json(t):
    # Style-Dictionary-ish shape
    out = {"color": {k.replace("_", "-"): {"value": v} for k, v in t["colors"].items()},
           "font": {k: {"value": v} for k, v in t["fonts"].items() if v},
           "radius": {"base": {"value": t["radius"]}} if t["radius"] else {}}
    return json.dumps(out, indent=2) + "\n"


EMITTERS = {"css": ("tokens.css", emit_css), "scss": ("_tokens.scss", emit_scss),
            "tailwind": ("tailwind.tokens.js", emit_tailwind), "json": ("tokens.json", emit_json)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design-json", required=True, help="design_system.py JSON ('-' for stdin)")
    ap.add_argument("--format", default="css", choices=list(EMITTERS) + ["all"])
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--print", action="store_true", dest="to_stdout")
    args = ap.parse_args()

    try:
        if args.design_json == "-":
            raw = sys.stdin.read()
        else:
            with open(args.design_json, encoding="utf-8") as fh:
                raw = fh.read()
        t = _tokens(json.loads(raw))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": "could not read design JSON: %s" % e}))
        sys.exit(1)

    formats = list(EMITTERS) if args.format == "all" else [args.format]
    written = []
    if not args.to_stdout:
        try:
            os.makedirs(args.out_dir, exist_ok=True)
        except OSError as e:
            print(json.dumps({"error": "could not create out-dir %s: %s" % (args.out_dir, e)}))
            sys.exit(1)
    for fmt in formats:
        fname, fn = EMITTERS[fmt]
        content = fn(t)
        if args.to_stdout:
            print(f"/* ---- {fname} ---- */\n{content}")
        else:
            path = os.path.join(args.out_dir, fname)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError as e:
                print(json.dumps({"error": "could not write %s: %s" % (path, e)}))
                sys.exit(1)
            written.append(path)
    if not args.to_stdout:
        print(json.dumps({"written": written}, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
