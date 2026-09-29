#!/usr/bin/env python3
"""
llms_txt.py — generate and validate /llms.txt (the community proposal for a Markdown
site summary aimed at LLMs and AI agents).

Format this implements (public proposal, restated):
  # Site or project name                      <- exactly one H1, first
  > One-paragraph summary                      <- optional blockquote, strongly advised
  Free-form Markdown paragraphs/lists          <- optional context, no headings
  ## Section                                   <- H2 "file lists"
  - [Link title](https://absolute/url): note   <- one link per list item, note optional
  ## Optional                                  <- links an agent may skip for short context

Honesty note: no major answer engine has confirmed llms.txt as a ranking or citation
input (see references/shared/search-landscape-2026.md §8). It is cheap, low-confidence,
and useful for agents that do read it — so this tool makes a *correct* one, and the GEO
scorecard weights it lightest.

Usage:
  python3 llms_txt.py --validate llms.txt [--human]
  python3 llms_txt.py --generate site.json [--out llms.txt]
      site.json = {"name", "summary", "details"?, "sections": [{"title", "links":
                   [{"title", "url", "desc"?}]}], "optional"?: [links]}
  python3 llms_txt.py --from-urls urls.txt --name "Site" --summary "..." [--out llms.txt]
      groups URLs by first path segment into sections (titles from slugs)

Standard library only. Deterministic. No network.
"""
import argparse
import json
import re
import sys
from urllib.parse import urlparse

LINK_ITEM = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]\(([^)\s]+)\)\s*(?::\s*(.*))?$")
MAX_BYTES = 100 * 1024
MAX_LINKS = 200
PENALTY = {"error": 25, "warning": 8, "info": 0}


def validate(text):
    """Validate llms.txt content. Returns {ok, score, title, summary, sections,
    links, issues:[{severity, line, finding, fix}]}. Deterministic."""
    issues = []

    def add(sev, line, finding, fix):
        issues.append({"severity": sev, "line": line, "finding": finding, "fix": fix})

    lines = (text or "").splitlines()
    title, summary, sections, links = None, None, [], []
    h1s, seen_urls, current = 0, {}, None
    first_content = next((i for i, l in enumerate(lines) if l.strip()), None)
    if first_content is None:
        add("error", 0, "file is empty", "Start with '# <Site name>' and a '> summary' line.")
    for i, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        if re.match(r"^#\s+\S", line):
            h1s += 1
            if h1s == 1:
                title = line[1:].strip()
                if first_content is not None and i - 1 != first_content:
                    add("error", i, "H1 is not the first line",
                        "Move '# <Site name>' to the very top.")
            else:
                add("error", i, "more than one H1", "Keep exactly one '# ' heading.")
            continue
        if re.match(r"^##\s+\S", line):
            current = {"title": line[2:].strip(), "links": 0, "line": i}
            sections.append(current)
            continue
        if re.match(r"^#{3,}\s", line):
            add("info", i, "H3+ heading inside the file",
                "Only H1 (name) and H2 (sections) carry meaning; flatten deeper headings.")
            continue
        if line.startswith(">") and summary is None and not sections:
            summary = line.lstrip("> ").strip()
            continue
        m = LINK_ITEM.match(line)
        if m:
            name, url, _note = m.group(1), m.group(2), m.group(3)
            if current is None:
                add("warning", i, "link list item before any '## ' section",
                    "Put link lists under an H2 section heading.")
            else:
                current["links"] += 1
            links.append({"title": name, "url": url, "section": current["title"] if current else None})
            if not re.match(r"^https?://", url):
                add("warning", i, f"relative or non-http URL: {url}",
                    "Use absolute https:// URLs so agents can fetch them directly.")
            if url in seen_urls:
                add("warning", i, f"duplicate URL (first on line {seen_urls[url]}): {url}",
                    "List each URL once, in its best-fit section.")
            else:
                seen_urls[url] = i
            continue
        if current is not None and re.match(r"^\s*[-*]\s+", line):
            add("warning", i, "list item under a section is not a '[title](url)' link",
                "Format items as '- [Title](https://url): optional note'.")

    if title is None and first_content is not None:
        add("error", first_content + 1, "missing H1 site name",
            "The first line must be '# <Site or project name>'.")
    if summary is None and first_content is not None:
        add("warning", 0, "no '> ' blockquote summary",
            "Add a one-paragraph '> ' summary right under the H1.")
    for s in sections:
        if s["links"] == 0:
            add("warning", s["line"], f"section '{s['title']}' has no links",
                "Add '- [Title](url)' items or remove the empty section.")
    if not links and first_content is not None:
        add("warning", 0, "no links at all", "List the site's key pages under H2 sections.")
    size = len((text or "").encode("utf-8"))
    if size > MAX_BYTES:
        add("warning", 0, f"file is {size // 1024} KB",
            "Keep llms.txt a concise index (<100 KB); put full text in llms-full.txt.")
    if len(links) > MAX_LINKS:
        add("info", 0, f"{len(links)} links",
            "Curate: an index of the pages that matter beats a sitemap dump.")

    score = max(0, 100 - sum(PENALTY[x["severity"]] for x in issues))
    return {"ok": not any(x["severity"] == "error" for x in issues), "score": score,
            "title": title, "summary": summary,
            "sections": [{"title": s["title"], "links": s["links"]} for s in sections],
            "links": len(links), "issues": issues}


def _link_line(link):
    note = (": " + link["desc"].strip()) if link.get("desc") else ""
    return "- [%s](%s)%s" % (link["title"].strip(), link["url"].strip(), note)


def generate(site):
    """Render llms.txt from a site dict. Deterministic; raises ValueError on bad input."""
    if not isinstance(site, dict) or not site.get("name"):
        raise ValueError("site JSON needs at least a 'name'")
    out = ["# " + site["name"].strip(), ""]
    if site.get("summary"):
        out += ["> " + " ".join(site["summary"].split()), ""]
    if site.get("details"):
        out += [site["details"].strip(), ""]
    for sec in site.get("sections", []):
        items = [l for l in sec.get("links", []) if l.get("title") and l.get("url")]
        if not items:
            continue
        out += ["## " + sec["title"].strip(), ""] + [_link_line(l) for l in items] + [""]
    opt = [l for l in site.get("optional", []) if l.get("title") and l.get("url")]
    if opt:
        out += ["## Optional", ""] + [_link_line(l) for l in opt] + [""]
    return "\n".join(out).rstrip() + "\n"


def _title_from_slug(seg):
    seg = re.sub(r"\.(html?|php|aspx?)$", "", seg)
    words = re.split(r"[-_]+", seg)
    return " ".join(w.capitalize() for w in words if w) or "Home"


def site_from_urls(urls, name, summary=None):
    """Group URLs by first path segment into sections. Root URL -> 'Main'."""
    groups, seen = {}, set()
    for u in urls:
        u = u.strip()
        if not u or u in seen or not re.match(r"^https?://", u):
            continue
        seen.add(u)
        path = [p for p in urlparse(u).path.split("/") if p]
        key = path[0] if len(path) > 1 else "_main"
        title = _title_from_slug(path[-1]) if path else "Home"
        groups.setdefault(key, []).append({"title": title, "url": u})
    sections = []
    if "_main" in groups:
        sections.append({"title": "Main", "links": groups.pop("_main")})
    for key in sorted(groups):
        sections.append({"title": _title_from_slug(key), "links": groups[key]})
    return {"name": name, "summary": summary, "sections": sections}


def _human(v):
    print(f"llms.txt: {'VALID' if v['ok'] else 'INVALID'}  score {v['score']}/100  "
          f"title={v['title']!r}  sections={len(v['sections'])}  links={v['links']}")
    for x in v["issues"]:
        where = f"line {x['line']}: " if x["line"] else ""
        print(f"  [{x['severity'].upper()}] {where}{x['finding']} -> {x['fix']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="generate / validate llms.txt")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", help="llms.txt file to check")
    g.add_argument("--generate", help="site JSON (path or inline) to render")
    g.add_argument("--from-urls", help="file with one URL per line")
    ap.add_argument("--name", help="site name (with --from-urls)")
    ap.add_argument("--summary", help="one-paragraph summary (with --from-urls)")
    ap.add_argument("--out", help="write the generated file here")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)

    if a.validate:
        try:
            with open(a.validate, encoding="utf-8", errors="replace") as fh:
                v = validate(fh.read())
        except OSError as e:
            print(json.dumps({"error": f"could not read {a.validate}: {e}"}))
            return 1
        _human(v) if a.human else print(json.dumps(v, indent=2))
        return 0

    try:
        if a.generate:
            try:
                with open(a.generate, encoding="utf-8") as fh:
                    site = json.load(fh)
            except OSError:
                site = json.loads(a.generate)
        else:
            if not a.name:
                raise ValueError("--from-urls needs --name")
            with open(a.from_urls, encoding="utf-8") as fh:
                site = site_from_urls(fh.read().splitlines(), a.name, a.summary)
        text = generate(site)
    except (ValueError, OSError) as e:
        print(json.dumps({"error": str(e)}))
        return 1
    v = validate(text)
    if a.out:
        try:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as e:
            print(json.dumps({"error": f"could not write {a.out}: {e}"}))
            return 1
        print(json.dumps({"action": "generate", "out": a.out, "validation": v}, indent=2))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
