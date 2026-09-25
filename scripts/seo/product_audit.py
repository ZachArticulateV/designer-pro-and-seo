#!/usr/bin/env python3
"""
product_audit.py — e-commerce page audit: merchant-listing readiness for product pages,
index hygiene for category / faceted / paginated pages.

Product pages (--type product, auto-detected from Product/ProductGroup markup):
  P1  no Product / ProductGroup structured data
  P2  Product markup not eligible (schema_gen high findings: missing name/image/offer
      fields, bad price / currency, ...)            P3  value defects (medium)
  P4  offer without availability                    P5  no GTIN / MPN / brand identifier
  P6  no return policy (Offer or Organization)      P7  no shipping details
  P8  priceValidUntil in the past (with --as-of)
  P9  marked-up price not visible on the page       P10 rating markup with no visible rating
  P11 availability says InStock but the page says sold out / out of stock
  P12 several Product variants without a ProductGroup
  P13 no H1                                         P14 thin product description
Category pages (--type category, or auto when the URL carries filter/sort/page params):
  C1  filtered URL is self-canonical and indexable (facet index bloat)
  C2  paginated page canonicalizes to page 1 (hides deeper products)
  C3  paginated page is noindex                     C4  thin category copy
  C5  sort-order URL is indexable                   C6  no ItemList markup (info)

Every finding {code, severity, finding, fix}; deterministic 0-100 score per finding type.
Reuses schema_gen.py for JSON-LD extraction + validation (one source of truth).

Usage:
  python3 product_audit.py --file product.html --url https://shop/p/classic-bench [--as-of 2026-09-25] [--human]
  python3 product_audit.py --file list.html --url "https://shop/benches?color=red&page=2" --type category
  python3 product_audit.py --url https://shop/p/x                   # SSRF-guarded fetch

Standard library only.
"""
import argparse
import datetime as _dt
import json
import os
import re
import sys
from urllib.parse import urlparse, parse_qs, urljoin

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workflow"))
from net_safety import safe_open, UrlValidationError, SafeFetchError  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_gen  # noqa: E402

UA = "Mozilla/5.0 (compatible; designer-pro-seo-commerce/1.0)"
PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}
IDS = ("gtin", "gtin8", "gtin12", "gtin13", "gtin14", "mpn", "isbn")
PAGE_PARAMS = {"page", "p", "pg", "paged"}
SORT_PARAMS = {"sort", "sortby", "sort_by", "order", "orderby", "dir"}
TRACK_PARAMS = re.compile(r"^(utm_\w+|gclid|fbclid|msclkid|ref)$", re.I)
SOLD_OUT = re.compile(r"\b(out of stock|sold out|currently unavailable|no longer available)\b", re.I)


def visible_text(html):
    t = re.sub(r"(?is)<(script|style|noscript|template|svg)\b.*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;|&#160;", " ", t)
    return " ".join(t.split())


def _nodes(docs):
    out = []
    for d in docs:
        schema_gen._walk(d, lambda n: out.append(n) if schema_gen._first_type(n) else None)
    return out


def _price_visible(price, text):
    try:
        v = float(str(price).replace(",", ""))
    except ValueError:
        return True          # a malformed price is reported by schema validation instead
    whole = int(v)
    cents = round((v - whole) * 100)
    num = f"{whole:,}".replace(",", "[,.]?")
    frac = r"[.,]%02d" % cents if cents else r"(?:[.,]00)?"
    return re.search(r"(?<![\d.,])%s%s(?![\d])" % (num, frac), text) is not None


def _page_meta(html):
    canon = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', html, re.I)
    robots = re.search(r'<meta[^>]+name=["\']robots["\'][^>]*content=["\']([^"\']*)', html, re.I)
    h1 = len(re.findall(r"<h1[\s>]", html, re.I))
    return (canon.group(1) if canon else None,
            bool(robots and "noindex" in robots.group(1).lower()), h1)


def audit(html, url=None, page_type="auto", as_of=None):
    found = {}

    def add(code, sev, finding, fix, detail=None):
        f = found.setdefault(code, {"code": code, "severity": sev, "finding": finding,
                                    "fix": fix, "details": []})
        if detail and detail not in f["details"]:
            f["details"].append(detail)

    docs, errors = schema_gen.extract_jsonld(html)
    nodes = _nodes(docs)
    products = [n for n in nodes if schema_gen._first_type(n) == "Product"]
    groups = [n for n in nodes if schema_gen._first_type(n) == "ProductGroup"]
    orgs = [n for n in nodes if schema_gen.spec_type(schema_gen._first_type(n)) in schema_gen.ORG_TYPES]
    text = visible_text(html)
    canon, noindex, h1 = _page_meta(html)
    q = {k.lower(): v for k, v in parse_qs(urlparse(url or "").query).items()}

    if page_type == "auto":
        page_type = "product" if (products or groups) else "category" if (
            q or re.search(r'"@type"\s*:\s*"(ItemList|CollectionPage|OfferCatalog)"', html)) else "product"

    if page_type == "product":
        if not (products or groups):
            add("P1", "high", "no Product / ProductGroup structured data",
                "Add Product JSON-LD with name, image, offers (price, priceCurrency, availability).")
        for e in errors:
            add("P2", "high", "Product markup not eligible", "Fix the JSON syntax.", e)
        top = [n for n in products if not any(n is v for g in groups
                                              for v in schema_gen._as_list(g.get("hasVariant")))]
        for prod in (top or products)[:10] + groups[:3]:
            v = schema_gen.validate_obj(dict({"@context": "https://schema.org"}, **prod))
            for i in v["issues"]:
                if i["severity"] in ("critical", "high"):
                    add("P2", "high", "Product markup not eligible",
                        "Fix each listed property (see references/seo-schema/entity-graph.md).",
                        i["finding"])
                elif i["severity"] == "medium":
                    add("P3", "medium", "Product markup value defects",
                        "Correct the listed values.", i["finding"])
        org_returns = any(o.get("hasMerchantReturnPolicy") for o in orgs)
        org_shipping = any(o.get("shippingDetails") or o.get("hasShippingService") for o in orgs)
        for prod in products:
            offers = [o for o in schema_gen._as_list(prod.get("offers")) if isinstance(o, dict)]
            name = prod.get("name", "?")
            if not any(prod.get(k) for k in IDS) and not prod.get("brand"):
                add("P5", "medium", "no GTIN / MPN / brand identifier",
                    "Add gtin (or mpn) and brand so the product matches across merchants.", name)
            for o in offers:
                if not o.get("availability"):
                    add("P4", "medium", "offer without availability",
                        "Add availability (https://schema.org/InStock, OutOfStock, ...).", name)
                if not (o.get("hasMerchantReturnPolicy") or org_returns):
                    add("P6", "medium", "no return policy markup (Offer or Organization)",
                        "Declare hasMerchantReturnPolicy once on the Organization, or per Offer.", name)
                if not (o.get("shippingDetails") or org_shipping):
                    add("P7", "medium", "no shipping details markup",
                        "Add shippingDetails (OfferShippingDetails) with rate + delivery time.", name)
                pvu = schema_gen._as_list(o.get("priceValidUntil"))[0] if o.get("priceValidUntil") else None
                d = _parse_date(pvu) if isinstance(pvu, str) else None
                if as_of and d and d < as_of:
                    add("P8", "high", "priceValidUntil is in the past",
                        "Update or remove priceValidUntil; expired offers drop out of listings.", f"{name}: {pvu}")
                price = o.get("price")
                if price not in (None, "") and not _price_visible(price, text):
                    add("P9", "high", "marked-up price not visible on the page",
                        "Show the same price the markup states (markup must match visible content).",
                        f"{name}: {price}")
                av = str(o.get("availability", ""))
                if av.endswith("InStock") and SOLD_OUT.search(text):
                    add("P11", "high", "markup says InStock but the page says sold out",
                        "Keep availability in sync with the page and the feed.", name)
            ar = prod.get("aggregateRating")
            if isinstance(ar, dict) and ar.get("ratingValue") is not None:
                rv = str(ar.get("ratingValue"))
                cnt = str(ar.get("reviewCount") or ar.get("ratingCount") or "")
                if rv not in text and (not cnt or cnt not in text):
                    add("P10", "high", "rating markup with no visible rating on the page",
                        "Show the rating and review count on the page, or remove the markup "
                        "(hidden ratings risk a manual action).", name)
        if len(products) >= 2 and not groups:
            add("P12", "medium", f"{len(products)} Product nodes without a ProductGroup",
                "Model size/color variants as one ProductGroup with hasVariant + variesBy.")
        for g in groups:
            if not g.get("variesBy"):
                add("P12", "info", "ProductGroup without variesBy",
                    "Name the varying properties (e.g. https://schema.org/color).")
        if h1 == 0:
            add("P13", "high", "no H1", "Use the product name as the H1.")
        words = len(text.split())
        if words < 150:
            add("P14", "medium", f"thin product page ({words} visible words)",
                "Write an original description: materials, dimensions, use, care, who it's for.")
    else:
        filt = [k for k in q if k not in PAGE_PARAMS | SORT_PARAMS and not TRACK_PARAMS.match(k)]
        self_canon = canon and urljoin(url or "", canon).rstrip("/") == (url or "").rstrip("/")
        if filt and self_canon and not noindex:
            add("C1", "medium", "filtered URL is self-canonical and indexable (facet index bloat)",
                "Canonicalize filter combinations to the unfiltered category (or noindex them) "
                "unless the facet is a deliberate landing page.", ", ".join(filt))
        page_n = next((q[k][0] for k in PAGE_PARAMS if k in q), None) or \
            (re.search(r"/page/(\d+)", urlparse(url or "").path) or [None, None])[1]
        if page_n and page_n not in ("1", "0"):
            if canon and not self_canon and not re.search(r"page", canon, re.I):
                add("C2", "high", f"page {page_n} canonicalizes to page 1",
                    "Paginated pages should be self-canonical so deeper products stay discoverable.")
            if noindex:
                add("C3", "medium", f"paginated page {page_n} is noindex",
                    "Keep paginated pages indexable (self-canonical) so links to products are followed.")
        if any(k in q for k in SORT_PARAMS) and not noindex and (self_canon or not canon):
            add("C5", "medium", "sort-order URL is indexable",
                "Canonicalize sort variants to the default order.")
        words = len(text.split())
        if words < 80:
            add("C4", "medium", f"thin category page ({words} visible words)",
                "Add a short, useful intro (what's in the range, how to choose) above the grid.")
        if not re.search(r'"@type"\s*:\s*"ItemList"', html):
            add("C6", "info", "no ItemList markup",
                "Optional: ItemList of the product URLs helps machines read the listing.")

    order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    findings = sorted(found.values(), key=lambda f: (order[f["severity"]], f["code"][0],
                                                    int(f["code"][1:])))
    return {"action": "product-audit", "page_type": page_type, "products": len(products),
            "product_groups": len(groups), "findings": findings,
            "score": max(0, 100 - sum(PENALTY[f["severity"]] for f in findings)),
            "needs_tier1": ["Google Shopping / marketplace presence (DataForSEO Merchant)",
                            "Merchant Center feed diagnostics"]}


def _parse_date(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    try:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except ValueError:
        return None


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
    ap = argparse.ArgumentParser(description="e-commerce page audit")
    ap.add_argument("--file")
    ap.add_argument("--url")
    ap.add_argument("--type", default="auto", choices=("auto", "product", "category"))
    ap.add_argument("--as-of", help="YYYY-MM-DD for priceValidUntil checks")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args(argv)
    as_of = _parse_date(a.as_of) if a.as_of else None
    if a.as_of and not as_of:
        print(json.dumps({"error": "--as-of must be YYYY-MM-DD"}))
        return 1
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
    r = audit(html, a.url, a.type, as_of)
    if a.human:
        print(f"# E-commerce audit ({r['page_type']}): {a.file or a.url}  "
              f"{r['products']} product(s)  score {r['score']}/100")
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
