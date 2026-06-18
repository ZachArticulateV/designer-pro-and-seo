#!/usr/bin/env python3
"""
schema_gen.py — JSON-LD structured-data generator + validator.

Generates Schema.org JSON-LD (the only format Google recommends) and validates it
against Google's rich-results required/recommended properties. Encodes 2026
reality, including the FAQPage rich-result deprecation (May 7, 2026): FAQPage is
still valid Schema.org and useful for AI/semantic context, but no longer yields a
Google rich result, so the validator flags it.

Standard library only. Deterministic.

Usage:
  # generate (and auto-validate)
  python3 schema_gen.py --type LocalBusiness --data '{"name":"Acme","address":"1 Main St"}'
  # validate existing JSON-LD (file or inline JSON)
  python3 schema_gen.py --validate path/to/markup.json
  python3 schema_gen.py --list        # list known types + their required props
"""
import argparse
import json
import os
import sys

# Required / recommended properties per type (Google rich-results oriented, 2026).
# DEPRECATED_RICH = still valid schema, but no longer a Google rich result.
SPEC = {
    "Organization": {
        "required": ["name", "url"],
        "recommended": ["logo", "sameAs", "contactPoint"],
    },
    "LocalBusiness": {
        "required": ["name", "address"],
        "recommended": ["telephone", "geo", "openingHoursSpecification", "priceRange", "image", "url"],
    },
    "Article": {
        "required": ["headline", "author", "datePublished"],
        "recommended": ["image", "dateModified", "publisher"],
        "notes": "Use ISO 8601 for datePublished/dateModified.",
    },
    "Product": {
        "required": ["name", "image"],
        "recommended": ["description", "brand", "offers", "aggregateRating", "review", "sku", "gtin"],
        "notes": "offers should include price + priceCurrency + availability for merchant eligibility.",
    },
    "BreadcrumbList": {
        "required": ["itemListElement"],
        "recommended": [],
        "notes": "Each itemListElement is a ListItem with position + name + item.",
    },
    "FAQPage": {
        "required": ["mainEntity"],
        "recommended": [],
        "deprecated_rich": True,
        "notes": "FAQ rich results were deprecated by Google on 2026-05-07. Still valid schema and useful for AI/semantic context, but will not produce a Google rich result.",
    },
    "Event": {
        "required": ["name", "startDate", "location"],
        "recommended": ["endDate", "offers", "performer", "image", "eventStatus"],
    },
    "Person": {
        "required": ["name"],
        "recommended": ["url", "image", "sameAs", "jobTitle"],
    },
    "WebSite": {
        "required": ["name", "url"],
        "recommended": ["potentialAction"],
        "notes": "potentialAction (SearchAction) enables the sitelinks search box.",
    },
    "Review": {
        "required": ["itemReviewed", "reviewRating", "author"],
        "recommended": ["datePublished", "publisher"],
    },
    "VideoObject": {
        "required": ["name", "description", "thumbnailUrl", "uploadDate"],
        "recommended": ["duration", "contentUrl", "embedUrl"],
    },
}


def validate_obj(obj):
    """Validate one JSON-LD dict. Returns a findings dict."""
    findings = {"type": None, "missing_required": [], "missing_recommended": [],
                "warnings": [], "ok": False}
    t = obj.get("@type")
    if isinstance(t, list):
        t = t[0] if t else None
    findings["type"] = t
    if not obj.get("@context"):
        findings["warnings"].append('missing "@context" (should be "https://schema.org")')
    if t not in SPEC:
        findings["warnings"].append(f'no required-property spec for type "{t}" (validated context only)')
        findings["ok"] = not findings["missing_required"]
        return findings
    spec = SPEC[t]
    for p in spec["required"]:
        if p not in obj or obj.get(p) in (None, "", [], {}):
            findings["missing_required"].append(p)
    for p in spec.get("recommended", []):
        if p not in obj:
            findings["missing_recommended"].append(p)
    if spec.get("deprecated_rich"):
        findings["warnings"].append("DEPRECATED rich result: " + spec.get("notes", ""))
    elif spec.get("notes"):
        findings["warnings"].append(spec["notes"])
    findings["ok"] = not findings["missing_required"]
    return findings


def generate(type_name, data):
    obj = {"@context": "https://schema.org", "@type": type_name}
    obj.update(data)
    return obj


def _load_jsonld(arg):
    """arg may be a path to a .json file or an inline JSON string."""
    if os.path.exists(arg):
        with open(arg, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", help="Schema type to generate (see --list)")
    ap.add_argument("--data", default="{}", help="JSON object of properties")
    ap.add_argument("--validate", help="path or inline JSON-LD to validate")
    ap.add_argument("--list", action="store_true", help="list known types + required props")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args()

    if args.list:
        for t, s in SPEC.items():
            dep = " [rich-result DEPRECATED]" if s.get("deprecated_rich") else ""
            print(f"{t}{dep}: required={s['required']} recommended={s.get('recommended', [])}")
        return

    if args.validate:
        try:
            doc = _load_jsonld(args.validate)
        except (json.JSONDecodeError, OSError) as e:
            print(json.dumps({"error": f"could not parse JSON-LD: {e}"}))
            sys.exit(1)
        objs = doc if isinstance(doc, list) else [doc]
        report = {"validated": len(objs), "results": [validate_obj(o) for o in objs]}
        out = report
    elif args.type:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"--data is not valid JSON: {e}"}))
            sys.exit(1)
        obj = generate(args.type, data)
        out = {"jsonld": obj, "validation": validate_obj(obj)}
    else:
        print("Specify --type to generate, --validate to check, or --list.", file=sys.stderr)
        sys.exit(2)

    if args.human:
        print(json.dumps(out, indent=2))
        if "validation" in out:
            v = out["validation"]
            print("\n— validation —")
            print("OK" if v["ok"] else "MISSING REQUIRED: " + ", ".join(v["missing_required"]))
            for w in v["warnings"]:
                print("! " + w)
    else:
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
