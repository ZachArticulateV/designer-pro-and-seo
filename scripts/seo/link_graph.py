#!/usr/bin/env python3
"""
link_graph.py — internal-link architecture audit over a set of pages.

Builds the site's internal link graph and reports what crawlers and users feel:
  * orphans         pages nothing else links to (reachable only via sitemap, if at all)
  * click depth     BFS distance from the home page; pages deeper than 3 clicks
  * unreachable     pages no link path from home reaches (islands)
  * broken links    internal targets that are not in the page set
  * dead ends       pages with no outbound internal link
  * anchors         generic anchor text ("click here") and internal rel=nofollow
  * contextual      in-content inbound links per page (nav / header / footer excluded)
  * sitemap parity  (with --sitemap) orphaned sitemap URLs, linked pages missing from it

Inputs (offline):
  --dir BUILD_DIR --base-url https://site       every *.html file in a static build;
                                                 index.html -> folder URL
  --edges edges.json [--home URL]                {"page url": ["linked url", ...], ...}
                                                 e.g. from a crawler export

Each finding is {severity, code, finding, urls, count, fix}; a deterministic 0-100
score (100 − 25/critical − 10/high − 4/medium). Standard library only; no network.

Usage:
  python3 link_graph.py --dir dist/ --base-url https://example.com [--sitemap sitemap.xml] [--human]
  python3 link_graph.py --edges edges.json --home https://example.com/ [--human]
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}
DEEP = 3
GENERIC = {"click here", "here", "read more", "learn more", "more", "this", "link",
           "this page", "continue", "details", "more info", "go"}


def norm(url):
    """Canonical form for graph keys: lowercase scheme/host, no fragment, no
    index.html, no trailing slash except the root, query kept."""
    s = urlsplit(url)
    path = re.sub(r"/index\.html?$", "/", s.path or "/")
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit((s.scheme.lower(), s.netloc.lower(), path or "/", s.query, ""))


class _Links(HTMLParser):
    _CHROME = {"nav", "header", "footer", "aside"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self._chrome, self._a = [], 0, None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in self._CHROME:
            self._chrome += 1
        elif tag == "a" and a.get("href"):
            self._a = {"href": a["href"], "rel": a.get("rel", "").lower(),
                       "chrome": self._chrome > 0, "text": []}

    def handle_endtag(self, tag):
        if tag in self._CHROME:
            self._chrome = max(0, self._chrome - 1)
        elif tag == "a" and self._a is not None:
            self._a["text"] = " ".join("".join(self._a["text"]).split())
            self.links.append(self._a)
            self._a = None

    def handle_data(self, data):
        if self._a is not None:
            self._a["text"].append(data)


def extract(html, page_url):
    p = _Links()
    try:
        p.feed(html)
        p.close()
    except Exception:
        pass
    out = []
    for l in p.links:
        h = l["href"].strip()
        if h.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        u = urljoin(page_url, h)
        if urlsplit(u).scheme not in ("http", "https"):
            continue
        out.append({"to": norm(u), "rel": l["rel"], "chrome": l["chrome"], "text": l["text"]})
    return out


def pages_from_dir(root, base):
    base = base.rstrip("/") + "/"
    pages = {}
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            if not fn.lower().endswith((".html", ".htm")):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            url = norm(urljoin(base, rel))
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    pages[url] = extract(fh.read(), urljoin(base, rel))
            except OSError:
                continue
    return pages


def pages_from_edges(edges):
    pages = {}
    for src, targets in edges.items():
        pages[norm(src)] = [{"to": norm(urljoin(src, t)), "rel": "", "chrome": False, "text": ""}
                            for t in (targets or []) if isinstance(t, str)]
    return pages


def analyze(pages, home, complete=True, sitemap=None):
    host = urlsplit(home).netloc.lower()
    home = norm(home)
    issues = []

    def add(sev, code, finding, urls, fix):
        urls = sorted(urls)
        issues.append({"severity": sev, "code": code, "finding": finding,
                       "urls": urls[:15], "count": len(urls), "fix": fix})

    inbound = {u: set() for u in pages}
    contextual = {u: 0 for u in pages}
    anchors, broken, nofollow, edges = {}, {}, [], 0
    for src, links in pages.items():
        for l in links:
            t = l["to"]
            if urlsplit(t).netloc.lower() != host:
                continue
            edges += 1
            if "nofollow" in l["rel"].split():
                nofollow.append(src)
            if t not in pages:
                broken.setdefault(t, set()).add(src)
                continue
            if t != src:
                inbound[t].add(src)
                if not l["chrome"]:
                    contextual[t] += 1
            if l["text"]:
                anchors.setdefault(t, []).append(l["text"].lower().strip(" .!>"))

    # click depth (BFS over all internal links, nav included — that's how crawlers walk)
    depth = {}
    if home in pages:
        depth[home] = 0
        q = deque([home])
        while q:
            u = q.popleft()
            for l in pages[u]:
                t = l["to"]
                if t in pages and t not in depth:
                    depth[t] = depth[u] + 1
                    q.append(t)
    else:
        add("high", "L0", "home page not in the page set", [home],
            "Include the home page so click depth can be measured.")

    orphans = [u for u in pages if u != home and not inbound[u]]
    unreachable = [u for u in pages if u not in depth and u not in orphans and home in pages]
    deep = [u for u, d in depth.items() if d > DEEP]
    dead = [u for u, links in pages.items()
            if not any(urlsplit(l["to"]).netloc.lower() == host and l["to"] != u for l in links)]
    no_context = [u for u in pages if u != home and inbound[u] and contextual[u] == 0]
    generic = [t for t, texts in anchors.items() if texts and all(x in GENERIC for x in texts)]

    if orphans:
        add("high", "L1", f"{len(orphans)} orphan page(s) (no internal link points to them)",
            orphans, "Link each from its hub/category page and 1-2 related pages.")
    if unreachable:
        add("high", "L2", f"{len(unreachable)} page(s) unreachable from home (link islands)",
            unreachable, "Connect the island to the main navigation or a hub page.")
    if broken and complete:
        add("high", "L3", f"{len(broken)} broken internal link target(s)", list(broken),
            "Fix the href or restore the page; update every linking page.")
    elif broken:
        add("info", "L3", f"{len(broken)} internal target(s) outside the supplied page set",
            list(broken), "Crawl them to confirm they resolve.")
    if deep:
        add("medium", "L4", f"{len(deep)} page(s) deeper than {DEEP} clicks from home", deep,
            "Flatten: link important pages from hubs or the home page.")
    if dead:
        add("medium", "L5", f"{len(dead)} dead-end page(s) with no internal outlinks", dead,
            "Add a next step: related pages, the parent hub, a call to action.")
    if no_context:
        add("medium", "L6", f"{len(no_context)} page(s) linked only from nav/header/footer",
            no_context, "Add contextual in-body links; they carry topical relevance.")
    if generic:
        add("medium", "L7", f"{len(generic)} page(s) reached only through generic anchors",
            generic, "Use descriptive anchors that name the destination topic.")
    if nofollow:
        add("medium", "L8", f"{len(nofollow)} internal link(s) marked rel=nofollow",
            sorted(set(nofollow)), "Remove nofollow from internal links; use noindex or "
                                   "robots rules to keep pages out instead.")
    if sitemap is not None:
        sm = {norm(u) for u in sitemap}
        sm_orphans = [u for u in orphans if u in sm]
        missing = [u for u in pages if u not in sm]
        if sm_orphans:
            add("medium", "L9", f"{len(sm_orphans)} sitemap URL(s) are orphans in the link graph",
                sm_orphans, "A sitemap entry is a hint, not a link; link these pages too.")
        if missing:
            add("info", "L10", f"{len(missing)} linked page(s) not in the sitemap", missing,
                "Add them if they are canonical and indexable.")

    dist = {}
    for d in depth.values():
        dist[str(d)] = dist.get(str(d), 0) + 1
    top = sorted(((len(v), u) for u, v in inbound.items()), reverse=True)[:5]
    return {"action": "link-graph", "home": home, "pages": len(pages), "internal_links": edges,
            "depth_distribution": dict(sorted(dist.items(), key=lambda kv: int(kv[0]))),
            "max_depth": max(depth.values()) if depth else None,
            "top_linked": [{"url": u, "inbound": n} for n, u in top],
            "issues": issues,
            "score": max(0, 100 - sum(PENALTY[i["severity"]] for i in issues)),
            "ok": not any(i["severity"] in ("critical", "high") for i in issues)}


def _sitemap_urls(path):
    root = ET.parse(path).getroot()
    return [(e.text or "").strip() for e in root.iter()
            if e.tag.endswith("}loc") or e.tag == "loc"]


def _human(r):
    print(f"# Internal link graph: {r['pages']} pages, {r['internal_links']} internal links, "
          f"max depth {r['max_depth']}  score {r['score']}/100")
    print("  depth distribution: " + ", ".join(f"{k}:{v}" for k, v in r["depth_distribution"].items()))
    for i in r["issues"]:
        print(f"[{i['severity'].upper()}] {i['code']} {i['finding']}")
        for u in i["urls"][:5]:
            print(f"    - {u}")
        if i["fix"] and i["severity"] != "info":
            print(f"    fix: {i['fix']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="internal-link graph audit")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="static build directory of .html files")
    src.add_argument("--edges", help="JSON {page: [linked urls]}")
    ap.add_argument("--base-url", help="site URL the --dir maps to (required with --dir)")
    ap.add_argument("--home", help="home URL (default: --base-url, or the first edges key)")
    ap.add_argument("--sitemap", help="sitemap.xml for parity checks")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)

    try:
        if a.dir:
            if not a.base_url or not os.path.isdir(a.dir):
                raise ValueError("--dir needs an existing directory and --base-url")
            pages = pages_from_dir(a.dir, a.base_url)
            home, complete = a.home or a.base_url, True
        else:
            with open(a.edges, encoding="utf-8") as fh:
                edges = json.load(fh)
            if not isinstance(edges, dict) or not edges:
                raise ValueError("--edges must be a non-empty JSON object")
            pages = pages_from_edges(edges)
            home, complete = a.home or next(iter(edges)), False
        sitemap = _sitemap_urls(a.sitemap) if a.sitemap else None
    except (OSError, ValueError, ET.ParseError) as e:
        print(json.dumps({"error": str(e)}))
        return 1
    if not pages:
        print(json.dumps({"error": "no pages found"}))
        return 1
    r = analyze(pages, home, complete, sitemap)
    _human(r) if a.human else print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
