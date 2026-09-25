#!/usr/bin/env python3
"""
qa_gate.py — the static path of the 9-phase pre-delivery QA gate, as one command.

Runs the plugin's own engines over a build (one HTML file, or every page in a build
directory) and folds their findings into the qa-gate verdict:

  1 Functional       broken internal links (link_graph), placeholder href="#",
                     forms with no action
  2 Visual fidelity  N/A — needs Playwright / design-visual-qa
  3 Accessibility    a11y_static (structural WCAG 2.2)
  4 Performance      tech_audit cwv lab risks + image_audit loading/size/format/CLS
  5 Security         HTTPS / mixed content / headers (tech_audit) + exposed-secret scan
  6 Content          leaked placeholders / lorem ipsum (content_audit), missing local
                     images (with --dir)
  7 SEO baseline     tech_audit (indexability, serp, structured data, JS render, URLs),
                     schema_gen --html validation, image alt/social
  8 Cross-device     N/A — needs Playwright
  9 Deployment       robots.txt (incl. a staging "Disallow: /" left on), sitemap.xml,
                     404 page, favicon, analytics tag (with --dir)

Verdict rule (from templates/qa-report-template.md): any CRITICAL => FAIL and
CLIENT-READY = NO; only WARN-level or lower => CONDITIONAL PASS; nothing above
recommendations => PASS. Findings repeated across pages are merged (the page list is
kept). Fix time is estimated per distinct finding (critical 1.5 h, high 0.75 h,
medium 0.25 h).

Usage:
  python3 qa_gate.py --file index.html --url https://client.example/ [--report] [--out qa.md]
  python3 qa_gate.py --dir dist/ --base-url https://client.example [--max-pages 50] [--report]

Standard library only; offline (no fetch). JSON by default; --report renders the
filled QA template.
"""
import argparse
import datetime as _dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for sub in ("workflow", "seo", "design"):
    sys.path.insert(0, os.path.join(ROOT, "scripts", sub))
import a11y_static  # noqa: E402
import content_audit  # noqa: E402
import image_audit  # noqa: E402
import link_graph  # noqa: E402
import schema_gen  # noqa: E402
import tech_audit  # noqa: E402

PHASES = {1: "Functional integrity", 2: "Visual fidelity", 3: "Accessibility (WCAG)",
          4: "Performance (CWV)", 5: "Security", 6: "Content completeness",
          7: "SEO baseline", 8: "Cross-device / browser", 9: "Deployment readiness"}
LIVE_ONLY = {2: "N/A — needs Playwright (design-visual-qa)",
             8: "N/A — needs Playwright"}
HOURS = {"critical": 1.5, "high": 0.75, "medium": 0.25, "info": 0.0}
A11Y_SEV = {"critical": "critical", "serious": "high", "moderate": "medium", "minor": "info"}
SECRETS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "critical", "AWS access key id"),
    (re.compile(r"sk_live_[0-9A-Za-z]{16,}"), "critical", "Stripe live secret key"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "critical", "private key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"), "critical", "GitHub token"),
    (re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"), "critical", "Slack token"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "high", "Google API key (confirm it is HTTP-referrer restricted)"),
]
ANALYTICS = re.compile(r"googletagmanager\.com|gtag\(|google-analytics\.com|plausible\.io|"
                       r"matomo|umami|clarity\.ms|segment\.com/analytics|posthog", re.I)


class Gate:
    def __init__(self):
        self.items = {}

    def add(self, phase, sev, finding, page, fix="", source=""):
        if sev not in HOURS:
            sev = "info"
        key = (phase, sev, finding)
        it = self.items.setdefault(key, {"phase": phase, "severity": sev, "finding": finding,
                                         "fix": fix, "source": source, "pages": []})
        if page and page not in it["pages"]:
            it["pages"].append(page)

    def page_checks(self, html, url, label):
        # tech_audit -> 4 / 5 / 7
        for c in tech_audit.analyze_html(html, url)["checks"]:
            if c["severity"] == "info" and not c["fix"]:
                continue
            phase = {"security": 5, "cwv": 4}.get(c["dimension"], 7)
            self.add(phase, c["severity"], c["finding"], label, c["fix"], "tech_audit")
        if url and not url.startswith("https://"):
            self.add(5, "critical", "Not served over HTTPS", label,
                     "Serve over HTTPS and 301 http:// to https://.", "tech_audit")
        # a11y -> 3
        for f in a11y_static.analyze(html)["findings"]:
            self.add(3, A11Y_SEV.get(f["severity"], "info"),
                     f"{f['message']} (WCAG {f['wcag']})", label, "", "a11y_static")
        # images -> 4 / 7
        for f in image_audit.audit(html, url)["findings"]:
            phase = 4 if f["dimension"] in ("loading", "size", "cls", "format", "responsive") else 7
            if f["severity"] == "info":
                continue
            self.add(phase, f["severity"], f["finding"], label, f["fix"], "image_audit")
        # content -> 6 (completeness only: the gate is not a content-strategy review)
        ca = content_audit.audit(html, url)
        for c in ca["checks"]:
            if c["dimension"] == "originality" and c["severity"] in ("critical", "high"):
                self.add(6, "critical" if "placeholder" in c["finding"].lower() else c["severity"],
                         c["finding"], label, c["fix"], "content_audit")
        # structured data -> 7
        docs, errors = schema_gen.extract_jsonld(html)
        for e in errors:
            self.add(7, "high", f"JSON-LD does not parse: {e}", label, "Fix the JSON syntax.", "schema_gen")
        for d in docs:
            for r in schema_gen.validate_doc(d):
                for i in r["issues"]:
                    if i["severity"] in ("critical", "high", "medium"):
                        self.add(7, i["severity"], i["finding"], label, i["fix"], "schema_gen")
        # functional -> 1
        if re.search(r"""<a\b[^>]*href=["']#["']""", html, re.I):
            self.add(1, "medium", 'placeholder links (href="#")', label,
                     "Point every link at its real destination.", "qa_gate")
        for form in re.findall(r"<form\b[^>]*>", html, re.I):
            if not re.search(r"\baction\s*=", form, re.I) and not re.search(r"\bon\w+\s*=|data-", form, re.I):
                self.add(1, "medium", "form with no action (may not submit)", label,
                         "Wire the form to its endpoint (or confirm the JS handler) and test a submission.",
                         "qa_gate")
        # security -> 5
        for rx, sev, what in SECRETS:
            if rx.search(html):
                self.add(5, sev, f"exposed secret in page source: {what}", label,
                         "Remove it from the client bundle and ROTATE the credential now.", "qa_gate")
        return ca

    def site_checks(self, root, base, pages):
        files = {n.lower() for n in os.listdir(root)}
        robots = os.path.join(root, "robots.txt")
        if "robots.txt" not in files:
            self.add(9, "high", "no robots.txt in the build", "", "Ship a robots.txt with a Sitemap: line.")
        else:
            with open(robots, encoding="utf-8", errors="replace") as fh:
                rtxt = fh.read()
            groups, maps = tech_audit.ai_crawlers.parse_robots(rtxt)
            if tech_audit.ai_crawlers.bot_status("Googlebot", groups) == "blocked":
                self.add(9, "critical", "robots.txt blocks Googlebot (staging rule left on?)", "robots.txt",
                         "Replace the staging robots.txt with the production one before launch.")
            if not maps:
                self.add(9, "medium", "robots.txt has no Sitemap: line", "robots.txt",
                         "Add 'Sitemap: <absolute sitemap URL>'.")
        if not any(n.startswith("sitemap") and n.endswith((".xml", ".xml.gz")) for n in files):
            self.add(9, "medium", "no sitemap.xml in the build", "",
                     "Generate one (sitemap_tools.py --generate) and reference it in robots.txt.")
        if not any(n in files for n in ("404.html", "404.htm")) and not os.path.isdir(os.path.join(root, "404")):
            self.add(9, "medium", "no custom 404 page", "", "Add a helpful 404 with search / key links.")
        htmls = list(pages.values())
        if "favicon.ico" not in files and not any(re.search(r'rel=["\'][^"\']*icon', h, re.I) for h in htmls):
            self.add(9, "medium", "no favicon", "", "Add favicon.ico and <link rel=icon> (and an apple-touch-icon).")
        if not any(ANALYTICS.search(h) for h in htmls):
            self.add(9, "medium", "no analytics tag detected", "",
                     "Confirm analytics (GA4 / GTM / Plausible / ...) is installed, or document why not.")
        # broken internal links + missing local images -> 1 / 6
        graph = link_graph.analyze(link_graph.pages_from_dir(root, base), base)
        for i in graph["issues"]:
            if i["code"] == "L3":
                for u in i["urls"]:
                    self.add(1, "high", f"broken internal link -> {u}", "", i["fix"], "link_graph")
        for label, html in pages.items():
            for src in re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)", html, re.I):
                if re.match(r"^(https?:|data:|//)", src):
                    continue
                path = os.path.normpath(os.path.join(root, src.split("?")[0].lstrip("/"))) if src.startswith("/") \
                    else os.path.normpath(os.path.join(root, os.path.dirname(label), src.split("?")[0]))
                if path.startswith(os.path.normpath(root)) and not os.path.exists(path):
                    self.add(6, "high", f"image file missing: {src}", label,
                             "Add the asset or fix the path.", "qa_gate")

    def verdict(self, phases_run):
        items = sorted(self.items.values(), key=lambda i: (list(HOURS).index(i["severity"]), i["phase"]))
        crit = [i for i in items if i["severity"] == "critical"]
        high = [i for i in items if i["severity"] == "high"]
        phase_status = {}
        for p in PHASES:
            if p in LIVE_ONLY:
                phase_status[p] = LIVE_ONLY[p]
            elif p not in phases_run:
                phase_status[p] = "N/A — needs --dir (build directory)"
            else:
                sevs = {i["severity"] for i in items if i["phase"] == p}
                phase_status[p] = ("FAIL" if "critical" in sevs else "WARN" if "high" in sevs else "PASS")
        if crit:
            status, ready = "FAIL", "NO"
            risk = "Critical" if (len(crit) >= 3 or any(i["phase"] == 5 for i in crit)) else "High"
        elif high:
            status, ready, risk = "CONDITIONAL PASS", "YES", "Medium"
        else:
            status, ready, risk = "PASS", "YES", "Low"
        hours = round(sum(HOURS[i["severity"]] for i in items) * 4) / 4
        return {"status": status, "risk": risk, "client_ready": ready, "fix_hours": hours,
                "phases": {str(p): phase_status[p] for p in PHASES},
                "counts": {s: sum(1 for i in items if i["severity"] == s) for s in HOURS},
                "items": items}


def _bullets(items, limit=25):
    if not items:
        return "- none"
    out = []
    for i in items[:limit]:
        where = f" [{', '.join(i['pages'][:3])}{' +%d' % (len(i['pages']) - 3) if len(i['pages']) > 3 else ''}]" if i["pages"] else ""
        out.append(f"- (P{i['phase']}) {i['finding']}{where}" + (f" — fix: {i['fix']}" if i["fix"] else ""))
    if len(items) > limit:
        out.append(f"- … {len(items) - limit} more in the JSON report")
    return "\n".join(out)


def render(v, project, target, date=None):
    path = os.path.join(ROOT, "templates", "qa-report-template.md")
    with open(path, encoding="utf-8") as fh:
        tpl = fh.read()
    tpl = re.sub(r"(?s)^---.*?---\s*", "", tpl)
    by = {s: [i for i in v["items"] if i["severity"] == s] for s in HOURS}
    note = {"FAIL": "Blocked: fix every critical issue, then re-run the gate.",
            "CONDITIONAL PASS": "Deliverable once the warnings are scheduled; no critical issues remain.",
            "PASS": "Ready to hand off."}[v["status"]]
    note += (" Static path: phases 2 and 8 need Playwright; field Core Web Vitals need "
             "seo-google (CrUX/PSI).")
    fills = {"project": project, "target": target, "date": date or _dt.date.today().isoformat(),
             "status": v["status"], "risk": v["risk"], "client_ready": v["client_ready"],
             "fix_hours": v["fix_hours"], "critical": _bullets(by["critical"]),
             "warnings": _bullets(by["high"]), "recommendations": _bullets(by["medium"]),
             "nice_to_haves": _bullets(by["info"], 10), "verdict_note": note}
    for p in PHASES:
        fills[f"p{p}"] = v["phases"][str(p)]
    for k, val in fills.items():
        tpl = tpl.replace("{{%s}}" % k, str(val))
    return tpl


def main(argv=None):
    ap = argparse.ArgumentParser(description="static pre-delivery QA gate")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="one HTML page")
    src.add_argument("--dir", help="build directory (audits every .html page)")
    ap.add_argument("--url", help="page URL for --file")
    ap.add_argument("--base-url", help="site URL for --dir")
    ap.add_argument("--max-pages", type=int, default=50)
    ap.add_argument("--project", default="(unnamed project)")
    ap.add_argument("--report", action="store_true", help="render the filled QA template")
    ap.add_argument("--as-of", help="report date (YYYY-MM-DD) for reproducible reports")
    ap.add_argument("--out", help="write the output here instead of stdout")
    a = ap.parse_args(argv)

    gate = Gate()
    phases = {1, 3, 4, 5, 6, 7}
    try:
        if a.file:
            with open(a.file, encoding="utf-8", errors="replace") as fh:
                gate.page_checks(fh.read(), a.url, os.path.basename(a.file))
            target = a.url or a.file
        else:
            if not a.base_url or not os.path.isdir(a.dir):
                raise ValueError("--dir needs an existing directory and --base-url")
            pages = {}
            for dp, dns, fns in os.walk(a.dir):
                dns.sort()
                for fn in sorted(fns):
                    if fn.lower().endswith((".html", ".htm")) and len(pages) < a.max_pages:
                        rel = os.path.relpath(os.path.join(dp, fn), a.dir).replace(os.sep, "/")
                        with open(os.path.join(dp, fn), encoding="utf-8", errors="replace") as fh:
                            pages[rel] = fh.read()
            if not pages:
                raise ValueError("no .html pages in --dir")
            base = a.base_url.rstrip("/") + "/"
            for rel, html in pages.items():
                gate.page_checks(html, base + re.sub(r"(^|/)index\.html?$", r"\1", rel), rel)
            gate.site_checks(a.dir, a.base_url, pages)
            phases.add(9)
            target = a.base_url
    except (OSError, ValueError) as e:
        print(json.dumps({"error": str(e)}))
        return 1

    v = gate.verdict(phases)
    v.update({"project": a.project, "target": target,
              "coverage": "static path: phases 2 and 8 need Playwright; phase 4 is lab "
                          "heuristics (field CWV via seo-google)"})
    out = render(v, a.project, target, a.as_of) if a.report else json.dumps(v, indent=2)
    if a.out:
        try:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(out)
        except OSError as e:
            print(json.dumps({"error": f"could not write {a.out}: {e}"}))
            return 1
        print(json.dumps({"out": a.out, "status": v["status"], "risk": v["risk"],
                          "client_ready": v["client_ready"]}))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
