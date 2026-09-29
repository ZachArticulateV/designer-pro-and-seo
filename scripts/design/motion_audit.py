#!/usr/bin/env python3
"""
motion_audit.py — motion accessibility + performance audit over CSS and HTML.

Reads CSS files and/or HTML (inline <style> blocks and style="" attributes) and reports:

  M1  animations/transitions exist but no prefers-reduced-motion query       (high)
  M2  keyframes or transitions animate layout properties (width, height,
      top/left/right/bottom, margin, padding) — jank, CLS and INP cost     (medium)
  M3  `transition: all`                                                       (medium)
  M4  UI transitions/animations over 1000 ms (over 500 ms = info)             (medium)
  M5  infinite animations not stopped under reduced motion (WCAG 2.2.2)       (medium)
  M6  autoplaying <video> without muted + controls, or looping without controls
                                                                             (medium)
  M7  scroll-behavior: smooth not reset under reduced motion                  (info)
  M8  focus outline removed (outline: none / 0 on :focus) without a
      :focus-visible replacement (WCAG 2.4.7)                                 (high)
  M9  more than 6 distinct durations — timing isn't tokenized                 (info)

"Stopped under reduced motion" means a @media (prefers-reduced-motion: reduce) block
exists that sets animation / transition to none (or a near-zero duration) — globally
(`*`, `html`, `body`, `:root`) or for the same selector.

Usage:
  python3 motion_audit.py --css styles.css [--css more.css] [--html page.html] [--human]

Standard library only. Deterministic. 0-100 score (100 − 10/high − 4/medium).
"""
import argparse
import json
import re
import sys

LAYOUT_PROPS = ("width", "height", "top", "left", "right", "bottom", "margin", "padding",
                "max-height", "max-width", "min-height", "min-width")
PENALTY = {"high": 10, "medium": 4, "info": 0}


def _strip_comments(css):
    return re.sub(r"(?s)/\*.*?\*/", "", css)


def _blocks(css):
    """Top-level rules as (selector_or_at, body). @media / @supports bodies are kept whole."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        sel = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        out.append((sel, css[j + 1:k - 1]))
        i = k
    return out


def _ms(v):
    m = re.match(r"^\s*([\d.]+)\s*(ms|s)\b", v)
    if not m:
        return None
    x = float(m.group(1))
    return x * 1000 if m.group(2) == "s" else x


def audit(css="", html=""):
    found = {}

    def add(code, sev, finding, fix, detail=None):
        f = found.setdefault(code, {"code": code, "severity": sev, "finding": finding,
                                    "fix": fix, "details": []})
        if detail and detail not in f["details"]:
            f["details"].append(detail)

    styles = [css or ""]
    styles += re.findall(r"(?is)<style\b[^>]*>(.*?)</style>", html or "")
    inline = re.findall(r"""(?is)\bstyle\s*=\s*["']([^"']*)["']""", html or "")
    styles.append("".join("x{%s}" % s for s in inline))
    sheet = _strip_comments("\n".join(styles))

    rules, reduced_bodies = [], []
    keyframes = {}
    for sel, body in _blocks(sheet):
        low = sel.lower()
        if low.startswith("@keyframes") or low.startswith("@-webkit-keyframes"):
            keyframes[sel.split()[-1]] = body
        elif low.startswith("@media") and "prefers-reduced-motion" in low and "reduce" in low:
            reduced_bodies.append(body)
        elif low.startswith("@media") or low.startswith("@supports") or low.startswith("@layer"):
            rules += _blocks(body)
        elif not low.startswith("@"):
            rules.append((sel, body))

    reduced_sel, reduced_global = set(), False
    for body in reduced_bodies:
        for sel, decl in _blocks(body):
            d = decl.lower()
            if re.search(r"(animation|transition)[\w-]*\s*:\s*(none|0?\.0*1m?s|0m?s)\b", d) or \
                    re.search(r"animation-play-state\s*:\s*paused", d):
                for s in sel.split(","):
                    s = s.strip()
                    reduced_sel.add(s)
                    if s in ("*", "html", "body", ":root") or s.startswith("*"):
                        reduced_global = True
            if "scroll-behavior" in d:
                reduced_sel.add("__scroll__")

    animated, durations = [], set()
    for sel, body in rules:
        d = body.lower()
        has_anim = re.search(r"\banimation(-name)?\s*:", d) and not re.search(r"\banimation\s*:\s*none", d)
        has_trans = re.search(r"\btransition(-property)?\s*:", d) and not re.search(r"\btransition\s*:\s*none", d)
        if has_anim or has_trans:
            animated.append(sel)
        for m in re.finditer(r"\btransition\s*:\s*([^;]+)", d):
            val = m.group(1)
            if re.match(r"\s*all\b", val) or re.search(r",\s*all\b", val):
                add("M3", "medium", "`transition: all`", "List the properties that change "
                    "(e.g. `transition: opacity 200ms, transform 200ms`).", sel)
            for prop in LAYOUT_PROPS:
                if re.search(r"(^|,)\s*%s\b" % re.escape(prop), val):
                    add("M2", "medium", "animates layout properties",
                        "Animate transform / opacity instead (GPU-composited, no reflow).",
                        f"{sel} ({prop})")
        for m in re.finditer(r"\btransition-property\s*:\s*([^;]+)", d):
            for prop in LAYOUT_PROPS:
                if re.search(r"\b%s\b" % re.escape(prop), m.group(1)):
                    add("M2", "medium", "animates layout properties",
                        "Animate transform / opacity instead (GPU-composited, no reflow).",
                        f"{sel} ({prop})")
        for m in re.finditer(r"\b(?:transition|animation)(?:-duration)?\s*:\s*([^;]+)", d):
            for tok in re.findall(r"[\d.]+m?s\b", m.group(1)):
                ms = _ms(tok)
                if ms is None or ms == 0:
                    continue
                durations.add(ms)
                if ms > 1000 and "infinite" not in m.group(1):
                    add("M4", "medium", "UI motion over 1000 ms",
                        "Keep UI transitions ~150-400 ms; long motion feels sluggish.", f"{sel} ({tok})")
                elif ms > 500 and "infinite" not in m.group(1):
                    add("M4i", "info", "UI motion over 500 ms", "Consider 200-400 ms.", f"{sel} ({tok})")
        if re.search(r"\binfinite\b", d) and not (reduced_global or sel.strip() in reduced_sel):
            add("M5", "medium", "infinite animation not stopped under reduced motion",
                "Stop or pause it in @media (prefers-reduced-motion: reduce) (WCAG 2.2.2).", sel)
        if re.search(r"scroll-behavior\s*:\s*smooth", d) and "__scroll__" not in reduced_sel:
            add("M7", "info", "smooth scrolling not reset under reduced motion",
                "Set scroll-behavior: auto inside the reduced-motion query.", sel)
        if re.search(r"outline\s*:\s*(none|0)\b", d) and ":focus" in sel and ":focus-visible" not in sel:
            add("M8", "high", "focus outline removed",
                "Keep a visible :focus-visible style (outline or ring with 3:1 contrast) (WCAG 2.4.7).", sel)

    for name, body in keyframes.items():
        for prop in LAYOUT_PROPS:
            if re.search(r"(^|[;{\s])%s\s*:" % re.escape(prop), body.lower()):
                add("M2", "medium", "animates layout properties",
                    "Animate transform / opacity instead (GPU-composited, no reflow).",
                    f"@keyframes {name} ({prop})")
                break

    if animated and not reduced_bodies:
        add("M1", "high", f"{len(animated)} animated rule(s) and no prefers-reduced-motion query",
            "Add @media (prefers-reduced-motion: reduce) { *, *::before, *::after { "
            "animation-duration: .01ms !important; animation-iteration-count: 1 !important; "
            "transition-duration: .01ms !important; scroll-behavior: auto !important; } }")
    if "M8" in found and any(":focus-visible" in s and re.search(r"outline\s*:\s*(?!none|0\b)|box-shadow", b.lower())
                             for s, b in rules):
        found.pop("M8")      # a visible :focus-visible replacement exists
    for v in re.findall(r"(?is)<video\b[^>]*>", html or ""):
        lv = v.lower()
        if ("autoplay" in lv and ("muted" not in lv or "controls" not in lv)) or \
                ("loop" in lv and "controls" not in lv):
            add("M6", "medium", "autoplaying / looping video without muted + controls",
                "Autoplay muted with controls, and pause it under reduced motion (WCAG 2.2.2).")
    if len(durations) > 6:
        add("M9", "info", f"{len(durations)} distinct motion durations",
            "Tokenize timing (e.g. --dur-fast 150ms / --dur-base 250ms / --dur-slow 400ms).",
            ", ".join("%gms" % d for d in sorted(durations)[:8]))

    order = {"high": 0, "medium": 1, "info": 2}
    findings = sorted(found.values(), key=lambda f: (order[f["severity"]], f["code"]))
    return {"action": "motion-audit", "animated_rules": len(animated),
            "reduced_motion_queries": len(reduced_bodies), "keyframes": len(keyframes),
            "findings": findings,
            "score": max(0, 100 - sum(PENALTY[f["severity"]] for f in findings)),
            "note": "static read of the CSS; JS-driven motion (GSAP, Framer Motion, "
                    "IntersectionObserver classes) needs a manual or Playwright check"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="motion accessibility + performance audit")
    ap.add_argument("--css", action="append", default=[], help="CSS file (repeatable)")
    ap.add_argument("--html", action="append", default=[], help="HTML file (repeatable)")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)
    if not (a.css or a.html):
        print(json.dumps({"error": "provide --css and/or --html"}))
        return 1
    try:
        css = "\n".join(open(p, encoding="utf-8", errors="replace").read() for p in a.css)
        html = "\n".join(open(p, encoding="utf-8", errors="replace").read() for p in a.html)
    except OSError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    r = audit(css, html)
    if a.human:
        print(f"# Motion audit: {r['animated_rules']} animated rule(s), "
              f"{r['reduced_motion_queries']} reduced-motion query(ies)  score {r['score']}/100")
        for f in r["findings"]:
            print(f"[{f['severity'].upper()}] {f['code']} {f['finding']}")
            for d in f["details"][:4]:
                print(f"    - {d}")
            if f["severity"] != "info":
                print(f"    fix: {f['fix']}")
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
