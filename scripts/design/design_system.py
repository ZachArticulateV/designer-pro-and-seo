#!/usr/bin/env python3
"""
design_system.py — CSV-backed design-system reasoning engine.

Given a product type, industry, and free-text style keywords, composes a complete
design system (pattern, style, palette, typography, effects, anti-patterns,
pre-delivery checklist) by scoring rows in the local data/ libraries.

Contract (see references/ENGINE-CONTRACTS.md):
  - stdout is JSON by default; --human prints an ASCII summary.
  - Tolerates missing CSVs AND weak matches: any dimension resolved with no real
    token overlap is flagged in "_fallbacks" (so an unknown input never silently
    returns an arbitrary first row as if confident).
  - Deterministic: same inputs -> same output. Standard library only.

Usage:
  python3 design_system.py --product-type saas-landing --industry saas \\
      --keywords "modern, trustworthy, minimal" [--human] [--data-dir PATH]
"""
import argparse
import csv
import json
import os
import re
import sys


def _data_dir(override=None):
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "data"))


def _load(data_dir, filename):
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        return None
    # Tolerate a non-UTF-8 data CSV (a hand-edited cp1252 file shouldn't crash the
    # engine); if it is truly unreadable, return None so the fallback path flags it.
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with open(path, newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def _tokens(s):
    return set(t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if t)


def _overlap(query_tokens, *fields):
    row_tokens = set()
    for fld in fields:
        row_tokens |= _tokens(fld)
    return len(query_tokens & row_tokens)


def pick_product(rows, product_type, industry, qtokens):
    """Returns (row_or_None, matched_bool)."""
    if not rows:
        return None, False
    for r in rows:
        if r.get("product_type", "").lower() == (product_type or "").lower():
            return r, True
    best, best_s = None, 0
    pt = _tokens(product_type) | _tokens(industry) | qtokens
    for r in rows:
        s = _overlap(pt, r.get("product_type"), r.get("industry"),
                     r.get("notes"), r.get("key_sections"), r.get("recommended_style"))
        if s > best_s:
            best, best_s = r, s
    return (best, True) if best_s > 0 else (rows[0], False)


def pick_style(rows, want_style, qtokens, mood_tokens):
    """Returns (row, matched_bool, override).

    `override` is (default_style, chosen_style) when the user's keywords explicitly
    name a style other than the product's recommended default; in that case the engine
    honors the stated intent and the caller records the swap in "_fallbacks", so an
    explicit style keyword is never silently discarded.
    """
    if not rows:
        return None, False, None
    want_lc = (want_style or "").lower()
    want_row = next((r for r in rows if r.get("style", "").lower() == want_lc), None)

    if want_row is not None:
        # A keyword set that explicitly NAMES another style on file overrides the
        # product default. "Names" means every token of that style's name appears in
        # the keywords (subset), so a lone common adjective ("clean", "dark", "soft")
        # can't hijack a multi-word style, and "brutalist" can't ambiguously match
        # "neo-brutalist". Ties prefer the most specific (longest) name, then CSV order.
        named, named_score = None, 0
        for r in rows:
            if r is want_row:
                continue
            name_tokens = _tokens(r.get("style"))
            if name_tokens and name_tokens <= qtokens and len(name_tokens) > named_score:
                named, named_score = r, len(name_tokens)
        if named is not None:
            return named, True, (want_row.get("style"), named.get("style"))
        return want_row, True, None

    # No exact default row on file: score by keyword/mood overlap (closest wins).
    best, best_s = None, 0
    q = qtokens | mood_tokens | _tokens(want_style)
    for r in rows:
        s = _overlap(q, r.get("style"), r.get("mood_tags"),
                     r.get("characteristics"), r.get("best_for"), r.get("summary"))
        if q & _tokens(r.get("avoid_for")):
            s -= 2
        if s > best_s:
            best, best_s = r, s
    return (best, True, None) if best_s > 0 else (rows[0], False, None)


def pick_palette(rows, industry, palette_mood, qtokens):
    if not rows:
        return None, False
    q = _tokens(industry) | _tokens(palette_mood) | qtokens
    best, best_overlap = None, 0
    for r in rows:
        ov = _overlap(q, r.get("industry"), r.get("mood"), r.get("tags"), r.get("name"))
        score = ov + (1 if r.get("aa_body_text") == "pass" else 0)
        if best is None or score > best[1]:
            best = (r, score, ov)
    return (best[0], best[2] > 0)


def pick_typography(rows, typo_mood, product_type, qtokens):
    if not rows:
        return None, False
    q = _tokens(typo_mood) | _tokens(product_type) | qtokens
    best, best_s = None, 0
    for r in rows:
        s = _overlap(q, r.get("mood"), r.get("best_for"), r.get("name"))
        if s > best_s:
            best, best_s = r, s
    return (best, True) if best_s > 0 else (rows[0], False)


EFFECT_DEFAULTS = {
    "minimal": dict(radius="6px", shadow="subtle (0 1px 2px rgba(0,0,0,.06))", motion="150ms ease-out"),
    "luxury-serif": dict(radius="2px", shadow="none / hairline border", motion="400ms ease"),
    "neo-brutalist": dict(radius="0px", shadow="hard offset (4px 4px 0 #000)", motion="120ms steps"),
    "soft-ui": dict(radius="16px", shadow="soft (0 8px 24px rgba(0,0,0,.08))", motion="250ms ease-in-out"),
    "glassmorphism": dict(radius="14px", shadow="blur + glow", motion="300ms ease"),
    "dark-tech": dict(radius="8px", shadow="glow accent", motion="180ms ease-out"),
    "claymorphism": dict(radius="22px", shadow="puffy dual-tone", motion="300ms spring"),
    "_default": dict(radius="8px", shadow="medium (0 4px 12px rgba(0,0,0,.08))", motion="200ms ease-out"),
}


def compose(args):
    data_dir = _data_dir(args.data_dir)
    qtokens = _tokens(args.keywords)
    fallbacks = []

    styles = _load(data_dir, "ui-styles.csv")
    palettes = _load(data_dir, "color-palettes.csv")
    fonts = _load(data_dir, "font-pairings.csv")
    uxrules = _load(data_dir, "ux-rules.csv")
    products = _load(data_dir, "product-types.csv")

    for name, rows in [("ui-styles", styles), ("color-palettes", palettes),
                       ("font-pairings", fonts), ("ux-rules", uxrules),
                       ("product-types", products)]:
        if rows is None:
            fallbacks.append(f"{name}.csv missing — used heuristic defaults")

    prod, prod_ok = pick_product(products, args.product_type, args.industry, qtokens)
    if products and not prod_ok:
        fallbacks.append("product-type: no match for inputs — used generic landing defaults")
    want_style = prod.get("recommended_style") if prod else None
    palette_mood = prod.get("palette_mood") if prod else None
    typo_mood = prod.get("typography_mood") if prod else None
    pattern = prod.get("recommended_pattern") if prod else "hero-centric"
    key_sections = (prod.get("key_sections") if prod else "hero;value;social-proof;features;cta")
    anti_from_product = (prod.get("anti_patterns") if prod else "")

    mood_tokens = _tokens(palette_mood) | _tokens(typo_mood)
    style, style_ok, style_override = pick_style(styles, want_style, qtokens, mood_tokens)
    palette, palette_ok = pick_palette(palettes, args.industry, palette_mood, qtokens)
    typo, typo_ok = pick_typography(fonts, typo_mood, args.product_type, qtokens)

    if styles and not style_ok:
        fallbacks.append("style: no strong match — returned closest available (refine keywords to improve)")
    elif style_override:
        fallbacks.append("style: keyword '%s' overrode the product default '%s' (drop the keyword to keep the default)"
                         % (style_override[1], style_override[0]))
    if palettes and not palette_ok:
        fallbacks.append("palette: no strong match — returned closest available")
    if fonts and not typo_ok:
        fallbacks.append("typography: no strong match — returned closest available")

    style_name = style.get("style") if style else (want_style or "minimal")
    effects = EFFECT_DEFAULTS.get(style_name, EFFECT_DEFAULTS["_default"])

    anti = []
    for chunk in [anti_from_product, (style.get("avoid_for") if style else "")]:
        anti += [a.strip() for a in re.split(r"[;,]", chunk or "") if a.strip()]
    anti = list(dict.fromkeys(anti))

    if uxrules:
        checklist = [r.get("rule") for r in uxrules if r.get("priority") in ("critical", "high")]
    else:
        checklist = [
            "One primary CTA per view",
            "Value proposition visible without scrolling",
            "Body text contrast >= 4.5:1",
            "Tap targets >= 44x44 px",
            "LCP < 2.5s, CLS < 0.1, INP < 200ms",
        ]

    result = {
        "input": {"product_type": args.product_type, "industry": args.industry,
                  "keywords": args.keywords},
        "pattern": pattern,
        "style": {
            "name": style_name,
            "summary": style.get("summary") if style else None,
            "characteristics": style.get("characteristics") if style else None,
            "best_for": style.get("best_for") if style else None,
        },
        "palette": ({
            "name": palette.get("name"), "primary": palette.get("primary"),
            "secondary": palette.get("secondary"), "accent": palette.get("accent"),
            "bg": palette.get("bg"), "surface": palette.get("surface"),
            "text": palette.get("text"), "success": palette.get("success"),
            "warning": palette.get("warning"), "error": palette.get("error"),
            "text_on_bg_contrast": palette.get("text_on_bg_contrast"),
            "on_primary": palette.get("on_primary"),
            "aa_body_text": palette.get("aa_body_text"),
        } if palette else None),
        "typography": ({
            "pairing": typo.get("name"), "heading_font": typo.get("heading_font"),
            "body_font": typo.get("body_font"), "heading_weight": typo.get("heading_weight"),
            "body_weight": typo.get("body_weight"), "google_fonts": typo.get("google_fonts"),
        } if typo else None),
        "effects": effects,
        "key_sections": [s.strip() for s in re.split(r"[;,]", key_sections) if s.strip()],
        "anti_patterns": anti,
        "pre_delivery_checklist": checklist,
        "_fallbacks": fallbacks,
    }
    return result


def to_human(d):
    out = ["=" * 60]
    p = d["input"]
    out.append(f"DESIGN SYSTEM  —  {p['product_type']} / {p['industry']}")
    out.append("=" * 60)
    out.append(f"Pattern:    {d['pattern']}")
    s = d["style"]
    out.append(f"Style:      {s['name']}" + (f" — {s['summary']}" if s.get('summary') else ""))
    pal = d["palette"]
    if pal:
        out.append("Palette:    " + pal["name"])
        out.append(f"  primary {pal['primary']}  secondary {pal['secondary']}  accent {pal['accent']}")
        out.append(f"  bg {pal['bg']}  surface {pal['surface']}  text {pal['text']}  (text/bg {pal['text_on_bg_contrast']}, AA {pal['aa_body_text']})")
        out.append(f"  on-primary text {pal.get('on_primary')}  |  success {pal['success']}  warning {pal['warning']}  error {pal['error']}")
    t = d["typography"]
    if t:
        out.append("Type:       " + f"{t['pairing']} — {t['heading_font']} {t['heading_weight']} / {t['body_font']} {t['body_weight']}")
    e = d["effects"]
    out.append(f"Effects:    radius {e['radius']} | shadow {e['shadow']} | motion {e['motion']}")
    out.append("Sections:   " + ", ".join(d["key_sections"]))
    if d["anti_patterns"]:
        out.append("Avoid:      " + ", ".join(d["anti_patterns"]))
    out.append("")
    out.append("Pre-delivery checklist:")
    for c in d["pre_delivery_checklist"]:
        out.append(f"  [ ] {c}")
    if d["_fallbacks"]:
        out.append("")
        out.append("Notes (fallbacks):")
        for fb in d["_fallbacks"]:
            out.append(f"  ! {fb}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Compose a design system from local data libraries.")
    ap.add_argument("--product-type", default="", help="e.g. saas-landing, restaurant, luxury-brand")
    ap.add_argument("--industry", default="", help="e.g. saas, healthcare, ecommerce")
    ap.add_argument("--keywords", default="", help="free-text style keywords, comma separated")
    ap.add_argument("--data-dir", default=None, help="override path to data/ dir")
    ap.add_argument("--human", action="store_true", help="print ASCII summary instead of JSON")
    args = ap.parse_args()
    result = compose(args)
    print(to_human(result) if args.human else json.dumps(result, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
