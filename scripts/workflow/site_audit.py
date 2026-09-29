#!/usr/bin/env python3
"""
site_audit.py — the seo-audit orchestrator's free, local path in one command.

Runs every bundled SEO engine that applies to a static build (or one page), converts
each into the specialist score the seo-audit agents report, and rolls them up with
audit_aggregate.py (re-normalized over the specialists that actually ran). Output: one
weighted health score, the per-specialist breakdown, an explicit covered / not-covered
list, and ONE deduplicated fix list (critical -> high -> medium) with the pages each
finding affects.

Specialist  <- engine (score)
  seo-technical   tech_audit lab score, mean over pages, minus site-level robots findings
  seo-content     content_audit score, mean over pages
  seo-page        mean of the page's technical and content scores
  seo-schema      70% schema_gen validation (pages without JSON-LD score 40) + 30% the
                  cross-page @id graph score
  seo-sitemap     mean of sitemap_tools --validate and link_graph (no sitemap = graph
                  score − 10)
  seo-image-audit image_audit score (with --assets = the build), mean over pages with images
  seo-geo         geo_check scorecard (citability + structured data + robots + llms.txt)
  seo-ecommerce   product_audit score over pages with Product markup   (conditional)
  seo-hreflang    hreflang cluster score when any page carries hreflang (conditional)
Not run locally (listed in not_covered with what they need): seo-local-unified
(NAP listings / geo-grid ranks), seo-google (CrUX / GSC key), seo-backlinks (link source).

Usage:
  python3 site_audit.py --dir dist/ --base-url https://site.com [--as-of 2026-09-25] [--human]
  python3 site_audit.py --file page.html --url https://site.com/page [--human]

Standard library only; offline; deterministic for a given build and --as-of.
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
import audit_aggregate  # noqa: E402
import content_audit  # noqa: E402
import geo_check  # noqa: E402
import hreflang_tools  # noqa: E402
import image_audit  # noqa: E402
import link_graph  # noqa: E402
import llms_txt  # noqa: E402
import product_audit  # noqa: E402
import schema_gen  # noqa: E402
import site_map  # noqa: E402  (URL -> page-type heuristic)
import sitemap_tools  # noqa: E402
import tech_audit  # noqa: E402

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2}
PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}
# site_map's URL classes -> content_audit page types (depth floor + article-only E-E-A-T rules)
PAGE_TYPE = {"home": "home", "article": "article", "docs": "article", "product": "product",
             "category": "category"}
NOT_LOCAL = {
    "seo-local-unified": "needs NAP listings / geo-grid rank data (run nap_check.py / geogrid.py)",
    "seo-google": "needs a CrUX / PSI / Search Console key or MCP (field CWV, rankings)",
    "seo-backlinks": "needs a backlink source (Common Crawl path, Moz, Bing, DataForSEO)",
}


class Fixes:
    def __init__(self):
        self.items = {}

    def add(self, specialist, sev, finding, page, fix=""):
        if sev not in SEV_ORDER:
            return
        key = (specialist, sev, re.sub(r"\d+(\.\d+)?", "#", finding))   # "8 words" == "5 words"
        it = self.items.setdefault(key, {
            "specialist": specialist, "severity": sev, "finding": finding, "fix": fix, "pages": []})
        if finding != it["finding"]:
            it["varies_by_page"] = True
        if page and page not in it["pages"]:
            it["pages"].append(page)

    def ordered(self):
        return sorted(self.items.values(),
                      key=lambda i: (SEV_ORDER[i["severity"]], -len(i["pages"]), i["specialist"]))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs)) if xs else None


def run(pages, base, root=None, as_of=None):
    """pages: {label: (url, html)}. root: build dir (enables site-level checks)."""
    fx = Fixes()
    tech, content, page_scores, schema_scores, image_scores, geo_scores = [], [], [], [], [], []
    product_scores, docs_by_page, hreflang_pages = [], {}, {}
    robots = llms = None
    if root:
        rp, lp = os.path.join(root, "robots.txt"), os.path.join(root, "llms.txt")
        robots = open(rp, encoding="utf-8", errors="replace").read() if os.path.exists(rp) else None
        llms = open(lp, encoding="utf-8", errors="replace").read() if os.path.exists(lp) else None

    for label, (url, html) in pages.items():
        t = tech_audit.analyze_html(html, url)["checks"]
        ts = tech_audit.lab_score(t)
        tech.append(ts)
        for c in t:
            fx.add("seo-technical", c["severity"], c["finding"], label, c["fix"])
        ptype = PAGE_TYPE.get(site_map.classify_page_type(url or ""), "home")
        if re.search(r'"@type"\s*:\s*"(Product|ProductGroup)"', html):
            ptype = "product"
        ca = content_audit.audit(html, url, page_type=ptype, as_of=as_of)
        content.append(ca["score"])
        for c in ca["checks"]:
            fx.add("seo-content", c["severity"], f"({c['dimension']}) {c['finding']}", label, c["fix"])
        page_scores.append(round((ts + ca["score"]) / 2))

        docs, errors = schema_gen.extract_jsonld(html)
        docs_by_page[label] = docs
        if docs or errors:
            s = schema_gen._summary([r for d in docs for r in schema_gen.validate_doc(d)], errors)
            schema_scores.append(s["score"])
            for r in s["results"]:
                for i in r["issues"]:
                    fx.add("seo-schema", i["severity"], i["finding"], label, i["fix"])
        else:
            schema_scores.append(40)

        ia = image_audit.audit(html, url, root)
        if ia["images"]:
            image_scores.append(ia["score"])
            for f in ia["findings"]:
                fx.add("seo-image-audit", f["severity"], f["finding"], label, f["fix"])

        text, ld = geo_check.strip_html(html)
        report = {"citability": geo_check.score_passages(text), "structured_data_blocks": ld,
                  "ai_crawler_policy": geo_check.analyze_robots(robots) if robots else None,
                  "llms_txt": ({"present": True, "validation": llms_txt.validate(llms)} if llms
                               else ({"present": False} if root else None))}
        geo_scores.append(geo_check.build_scorecard(report)["score"])

        if re.search(r'"@type"\s*:\s*"(Product|ProductGroup)"', html):
            pa = product_audit.audit(html, url, "product", as_of)
            product_scores.append(pa["score"])
            for f in pa["findings"]:
                fx.add("seo-ecommerce", f["severity"], f["finding"], label, f["fix"])
        info = hreflang_tools.extract_page(html)
        if info["alternates"]:
            hreflang_pages[url] = info

    specialists, detail = {}, {}
    site_pen = 0
    if root:
        if robots:
            for n in tech_audit.analyze_robots(robots):
                fx.add("seo-technical", n["severity"], n["msg"], "robots.txt")
                site_pen += PENALTY[n["severity"]]
        else:
            fx.add("seo-technical", "high", "no robots.txt", "", "Ship a robots.txt with a Sitemap: line.")
            site_pen += PENALTY["high"]
    specialists["seo-technical"] = max(0, _mean(tech) - site_pen)
    specialists["seo-content"] = _mean(content)
    specialists["seo-page"] = _mean(page_scores)
    graph = schema_gen.graph_check(docs_by_page)
    for i in graph["issues"]:
        fx.add("seo-schema", i["severity"], i["finding"], ", ".join(i["where"][:3]), i["fix"])
    specialists["seo-schema"] = round(0.7 * _mean(schema_scores) + 0.3 * graph["score"])
    detail["seo-schema"] = {"validation_mean": _mean(schema_scores), "graph_score": graph["score"]}
    if image_scores:
        specialists["seo-image-audit"] = _mean(image_scores)
    specialists["seo-geo"] = _mean(geo_scores)
    if root:
        lg = link_graph.analyze(link_graph.pages_from_dir(root, base), base)
        for i in lg["issues"]:
            fx.add("seo-sitemap", i["severity"], i["finding"], ", ".join(i["urls"][:3]), i["fix"])
        sm = next((os.path.join(root, n) for n in sorted(os.listdir(root))
                   if n.lower().startswith("sitemap") and n.lower().endswith((".xml", ".xml.gz"))), None)
        if sm:
            v = sitemap_tools.validate(sm, as_of)
            for i in v["issues"]:
                fx.add("seo-sitemap", i["severity"], i["finding"], os.path.basename(sm), i["fix"])
            specialists["seo-sitemap"] = round((v["score"] + lg["score"]) / 2)
            detail["seo-sitemap"] = {"sitemap_score": v["score"], "link_graph_score": lg["score"]}
        else:
            fx.add("seo-sitemap", "high", "no sitemap.xml in the build", "",
                   "Generate one with sitemap_tools.py --generate and reference it in robots.txt.")
            specialists["seo-sitemap"] = max(0, lg["score"] - 10)
            detail["seo-sitemap"] = {"sitemap_score": None, "link_graph_score": lg["score"]}
    if product_scores:
        specialists["seo-ecommerce"] = _mean(product_scores)
    if hreflang_pages:
        hc = hreflang_tools.cluster(hreflang_pages)
        for i in hc["issues"]:
            fx.add("seo-hreflang", i["severity"], i["finding"], ", ".join(i["pages"][:3]), i["fix"])
        specialists["seo-hreflang"] = hc["score"]

    specialists = {k: v for k, v in specialists.items() if v is not None}
    agg = audit_aggregate.aggregate(specialists)
    not_covered = dict(NOT_LOCAL)
    if not image_scores:
        not_covered["seo-image-audit"] = "no images found"
    if not product_scores:
        not_covered["seo-ecommerce"] = "no Product markup detected (not a store page set)"
    if not hreflang_pages:
        not_covered["seo-hreflang"] = "no hreflang annotations (single-locale site)"
    if not root:
        not_covered["seo-sitemap"] = "needs --dir (the build) for sitemap + link graph"
    return {"action": "site-audit", "pages": len(pages), "health": agg,
            "specialists": specialists, "detail": detail,
            "covered": sorted(specialists), "not_covered": not_covered,
            "fixes": fx.ordered(),
            "needs_tier1": ["field Core Web Vitals (seo-google)", "rankings / impressions (GSC)",
                            "backlink profile", "AI-answer citation share"]}


def _human(r):
    h = r["health"]
    print(f"# SEO health: {h.get('overall_score')}/100 (grade {h.get('grade')}) over {r['pages']} page(s)")
    for name in sorted(r["specialists"], key=lambda n: -r["specialists"][n]):
        print(f"  - {name:<16} {r['specialists'][name]:>3}")
    for name, why in sorted(r["not_covered"].items()):
        print(f"  - {name:<16} n/a  ({why})")
    fixes = r["fixes"]
    print(f"\n{len(fixes)} fixes (critical -> high -> medium):")
    for f in fixes[:40]:
        where = f" [{len(f['pages'])} page(s)]" if len(f["pages"]) > 1 else (
            f" [{f['pages'][0]}]" if f["pages"] else "")
        if f.get("varies_by_page"):
            where += " (value varies by page)"
        print(f"[{f['severity'].upper()}] ({f['specialist']}) {f['finding']}{where}")
    if len(fixes) > 40:
        print(f"... {len(fixes) - 40} more in the JSON output")


def main(argv=None):
    ap = argparse.ArgumentParser(description="local one-command SEO site audit")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="static build directory")
    src.add_argument("--file", help="one HTML page")
    ap.add_argument("--base-url", help="site URL for --dir")
    ap.add_argument("--url", help="page URL for --file")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--as-of", help="YYYY-MM-DD for date-based checks")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)
    as_of = None
    if a.as_of:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", a.as_of)
        if not m:
            print(json.dumps({"error": "--as-of must be YYYY-MM-DD"}))
            return 1
        as_of = _dt.date(*map(int, m.groups()))
    try:
        if a.file:
            with open(a.file, encoding="utf-8", errors="replace") as fh:
                pages = {os.path.basename(a.file): (a.url, fh.read())}
            r = run(pages, a.url or "", None, as_of)
        else:
            if not a.base_url or not os.path.isdir(a.dir):
                raise ValueError("--dir needs an existing directory and --base-url")
            base = a.base_url.rstrip("/") + "/"
            pages = {}
            for dp, dns, fns in os.walk(a.dir):
                dns.sort()
                for fn in sorted(fns):
                    if fn.lower().endswith((".html", ".htm")) and len(pages) < a.max_pages:
                        rel = os.path.relpath(os.path.join(dp, fn), a.dir).replace(os.sep, "/")
                        with open(os.path.join(dp, fn), encoding="utf-8", errors="replace") as fh:
                            pages[rel] = (base + re.sub(r"(^|/)index\.html?$", r"\1", rel), fh.read())
            if not pages:
                raise ValueError("no .html pages in --dir")
            r = run(pages, a.base_url, a.dir, as_of)
    except (OSError, ValueError) as e:
        print(json.dumps({"error": str(e)}))
        return 1
    _human(r) if a.human else print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
