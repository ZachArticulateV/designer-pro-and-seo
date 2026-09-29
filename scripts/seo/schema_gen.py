#!/usr/bin/env python3
"""
schema_gen.py — JSON-LD structured-data generator, validator and entity-graph checker.

Modes:
  --list                      known types, their required/recommended props, rich status
  --type T --data JSON        generate one node (auto-validated)
  --validate FILE|JSON        validate JSON-LD (a node, a list, or an @graph document)
  --html FILE [FILE ...]      extract every application/ld+json block from HTML and validate
  --graph FILE [FILE ...]     cross-page @id graph check over HTML/JSON sources
                              (dangling references, conflicting definitions, a split
                              Organization entity, missing hub entities); alias --graph-check
  --site JSON                 emit a linked Organization + WebSite + WebPage (+ Breadcrumb)
                              @graph starter with stable #fragment @ids

Validation goes beyond "is the property there":
  * @graph documents are flattened; nested typed values (Product.offers ->
    Offer, Offer.shippingDetails -> OfferShippingDetails, Organization
    .hasMerchantReturnPolicy -> MerchantReturnPolicy, ratings, reviews) are validated
    against their own spec;
  * "one of" requirements (a Product needs offers OR review OR aggregateRating);
  * value checks — ISO 8601 dates, dateModified >= datePublished, absolute URLs, numeric
    price with no currency symbol, ISO 4217 currency, schema.org availability /
    itemCondition enums, ratingValue inside worst..best, sequential breadcrumb positions;
  * subtype inheritance (BlogPosting -> Article, Dentist -> LocalBusiness, ...);
  * retired rich-result displays (FAQ ended 2026-05-07, HowTo, the 2025 set, practice
    problems) are flagged as info — valid markup, no visual — never as errors.

Every issue is a {type, severity, property, finding, fix} record; a deterministic
0-100 score (100 − 25/critical − 10/high − 4/medium) lets the audit orchestrator
weight the result. Dated facts: references/shared/search-landscape-2026.md.

Standard library only. Deterministic. No network.
"""
import argparse
import json
import os
import re
import sys

# --- the spec -------------------------------------------------------------------------
# required      : must be present and non-empty (Google-required, or this plugin's minimum
#                 where Google lists none — noted in `notes`)
# required_any  : list of alternatives groups; at least one member of each must exist
# recommended   : improves eligibility / disambiguation
# nested        : prop -> spec type used to validate a nested object value
# deprecated_rich: still valid schema, but no Google rich-result display any more
SPEC = {
    "Organization": {
        "required": ["name", "url"],
        "recommended": ["logo", "sameAs", "description", "contactPoint", "address"],
        "nested": {"hasMerchantReturnPolicy": "MerchantReturnPolicy",
                   "aggregateRating": "AggregateRating"},
        "notes": "Give it a stable @id (e.g. https://site/#organization) and reference it "
                 "from every page; merchants can declare hasMerchantReturnPolicy here once.",
    },
    "LocalBusiness": {
        "required": ["name", "address"],
        "recommended": ["telephone", "geo", "openingHoursSpecification", "priceRange",
                        "image", "url"],
        "nested": {"aggregateRating": "AggregateRating", "review": "Review"},
    },
    "WebSite": {
        "required": ["name", "url"],
        "recommended": ["alternateName", "publisher"],
        "notes": "WebSite supplies the site-name signal. The sitelinks search box was "
                 "removed, so a SearchAction potentialAction no longer yields a search box "
                 "(harmless to keep).",
    },
    "WebPage": {
        "required": ["name"],
        "recommended": ["url", "isPartOf", "breadcrumb", "primaryImageOfPage", "about"],
        "rich": False,
    },
    "BreadcrumbList": {
        "required": ["itemListElement"],
        "recommended": [],
        "notes": "Each itemListElement is a ListItem with position + name + item.",
    },
    "Article": {
        "required": ["headline", "author", "datePublished"],
        "recommended": ["image", "dateModified", "publisher"],
        "notes": "Use ISO 8601 for datePublished/dateModified. (Google lists no hard "
                 "requirement; headline/author/datePublished is this plugin's minimum.)",
    },
    "Product": {
        "required": ["name", "image"],
        "required_any": [["offers", "review", "aggregateRating"]],
        "recommended": ["description", "brand", "sku", "gtin", "offers"],
        "nested": {"offers": "Offer", "aggregateRating": "AggregateRating",
                   "review": "Review"},
        "notes": "offers should include price + priceCurrency + availability for merchant eligibility.",
    },
    "ProductGroup": {
        "required": ["name"],
        "recommended": ["productGroupID", "variesBy", "hasVariant", "brand"],
        "nested": {"hasVariant": "Product"},
        "notes": "Variants (size/color) belong in one ProductGroup with hasVariant + variesBy.",
    },
    "Offer": {
        "required": ["priceCurrency"],
        "required_any": [["price", "priceSpecification"]],
        "recommended": ["availability", "url", "itemCondition", "shippingDetails",
                        "hasMerchantReturnPolicy", "priceValidUntil"],
        "nested": {"shippingDetails": "OfferShippingDetails",
                   "hasMerchantReturnPolicy": "MerchantReturnPolicy"},
    },
    "AggregateOffer": {
        "required": ["lowPrice", "priceCurrency"],
        "recommended": ["highPrice", "offerCount"],
    },
    "MerchantReturnPolicy": {
        "required": ["applicableCountry", "returnPolicyCategory"],
        "recommended": ["merchantReturnDays", "returnMethod", "returnFees"],
    },
    "OfferShippingDetails": {
        "required": ["shippingDestination"],
        "recommended": ["shippingRate", "deliveryTime"],
    },
    "AggregateRating": {
        "required": ["ratingValue"],
        "required_any": [["ratingCount", "reviewCount"]],
        "recommended": ["bestRating", "worstRating"],
    },
    "Review": {
        "required": ["itemReviewed", "reviewRating", "author"],
        "recommended": ["datePublished", "publisher"],
        "nested_skip": ["itemReviewed"],   # implied by the parent when nested
    },
    "FAQPage": {
        "required": ["mainEntity"],
        "recommended": [],
        "deprecated_rich": True,
        "notes": "FAQ rich results were deprecated by Google on 2026-05-07. Still valid schema and useful for AI/semantic context, but will not produce a Google rich result.",
    },
    "HowTo": {
        "required": ["name", "step"],
        "recommended": ["image", "totalTime", "supply", "tool"],
        "deprecated_rich": True,
        "notes": "HowTo rich results were removed from Google Search. Still valid schema and useful machine context, but will not produce a rich result.",
    },
    "Event": {
        "required": ["name", "startDate", "location"],
        "recommended": ["endDate", "offers", "performer", "image", "eventStatus",
                        "eventAttendanceMode", "organizer"],
    },
    "Person": {
        "required": ["name"],
        "recommended": ["url", "image", "sameAs", "jobTitle"],
    },
    "ProfilePage": {
        "required": ["mainEntity"],
        "recommended": ["dateCreated", "dateModified"],
        "nested": {"mainEntity": "Person"},
        "notes": "Use for author/creator profile pages; mainEntity is the Person or Organization.",
    },
    "DiscussionForumPosting": {
        "required": ["author", "datePublished"],
        "required_any": [["text", "image", "video"]],
        "recommended": ["headline", "url", "comment", "interactionStatistic"],
    },
    "QAPage": {
        "required": ["mainEntity"],
        "recommended": [],
        "notes": "Only for pages where users submit answers to one question.",
    },
    "Recipe": {
        "required": ["name", "image"],
        "recommended": ["author", "datePublished", "description", "recipeIngredient",
                        "recipeInstructions", "totalTime", "recipeYield", "nutrition",
                        "aggregateRating"],
        "nested": {"aggregateRating": "AggregateRating"},
    },
    "JobPosting": {
        "required": ["title", "description", "datePosted", "hiringOrganization"],
        "required_any": [["jobLocation", "applicantLocationRequirements"]],
        "recommended": ["validThrough", "employmentType", "baseSalary", "identifier",
                        "directApply"],
    },
    "SoftwareApplication": {
        "required": ["name", "offers"],
        "required_any": [["aggregateRating", "review"]],
        "recommended": ["applicationCategory", "operatingSystem"],
        "nested": {"offers": "Offer", "aggregateRating": "AggregateRating"},
    },
    "VideoObject": {
        "required": ["name", "description", "thumbnailUrl", "uploadDate"],
        "recommended": ["duration", "contentUrl", "embedUrl"],
    },
    "ImageObject": {
        "required": ["contentUrl"],
        "recommended": ["license", "acquireLicensePage", "creator", "creditText",
                        "copyrightNotice"],
    },
    "ItemList": {
        "required": ["itemListElement"],
        "recommended": [],
    },
    "Dataset": {
        "required": ["name", "description"],
        "recommended": ["license", "creator", "distribution"],
        "rich": False,
        "notes": "Dataset markup powers Dataset Search only, not regular Search results.",
    },
    # retired rich-result displays (2025 simplification + 2026 practice problems)
    "ClaimReview": {"required": ["claimReviewed", "reviewRating"], "recommended": [],
                    "deprecated_rich": True,
                    "notes": "Claim Review rich results were retired in 2025."},
    "Course": {"required": ["name", "description"], "recommended": ["provider"],
               "deprecated_rich": True,
               "notes": "Course Info rich results were retired in 2025."},
    "SpecialAnnouncement": {"required": ["name", "datePosted"], "recommended": [],
                            "deprecated_rich": True,
                            "notes": "Special Announcement rich results were retired in 2025."},
    "Occupation": {"required": ["name"], "recommended": ["estimatedSalary"],
                   "deprecated_rich": True,
                   "notes": "Estimated Salary rich results were retired in 2025."},
    "Vehicle": {"required": ["name"], "recommended": ["offers"], "deprecated_rich": True,
                "notes": "Vehicle Listing rich results were retired in 2025."},
    "Quiz": {"required": ["hasPart"], "recommended": [], "deprecated_rich": True,
             "notes": "Practice Problem support ended in Search Console / Rich Results Test in Jan 2026."},
}

SUBTYPES = {
    "BlogPosting": "Article", "NewsArticle": "Article", "TechArticle": "Article",
    "ScholarlyArticle": "Article", "Report": "Article",
    "Corporation": "Organization", "NGO": "Organization", "OnlineStore": "Organization",
    "OnlineBusiness": "Organization", "EducationalOrganization": "Organization",
    "MedicalOrganization": "Organization", "GovernmentOrganization": "Organization",
    "Car": "Vehicle", "MobileApplication": "SoftwareApplication",
    "WebApplication": "SoftwareApplication", "VideoGame": "SoftwareApplication",
    "AboutPage": "WebPage", "ContactPage": "WebPage", "CollectionPage": "WebPage",
    "ItemPage": "WebPage", "SearchResultsPage": "WebPage",
}
LOCAL_BUSINESS_SUBTYPES = {
    "Restaurant", "Cafe", "CafeOrCoffeeShop", "Bakery", "BarOrPub", "Dentist", "Physician",
    "MedicalClinic", "Hospital", "Pharmacy", "Plumber", "Electrician", "HVACBusiness",
    "RoofingContractor", "GeneralContractor", "HomeAndConstructionBusiness", "LegalService",
    "Attorney", "AccountingService", "FinancialService", "RealEstateAgent", "AutoRepair",
    "AutoDealer", "Store", "ClothingStore", "HardwareStore", "FurnitureStore",
    "HairSalon", "BeautySalon", "DaySpa", "HealthClub", "ExerciseGym", "Hotel", "LodgingBusiness",
    "ChildCare", "Preschool", "VeterinaryCare", "ProfessionalService", "EmergencyService",
    "MovingCompany", "Locksmith", "HousePainter", "LandscapingBusiness"}
for _t in LOCAL_BUSINESS_SUBTYPES:
    SUBTYPES.setdefault(_t, "LocalBusiness")

ORG_TYPES = {"Organization", "LocalBusiness"}
DATE_PROPS = {"datePublished", "dateModified", "uploadDate", "startDate", "endDate",
              "datePosted", "validThrough", "priceValidUntil", "dateCreated", "validFrom"}
URL_PROPS = {"url", "item", "contentUrl", "embedUrl", "thumbnailUrl", "logo", "image",
             "sameAs", "acquireLicensePage", "license"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$")
AVAILABILITY = {"InStock", "OutOfStock", "PreOrder", "BackOrder", "Discontinued",
                "InStoreOnly", "LimitedAvailability", "OnlineOnly", "SoldOut",
                "PreSale", "Reserved", "MadeToOrder"}
CONDITION = {"NewCondition", "UsedCondition", "RefurbishedCondition", "DamagedCondition"}
PENALTY = {"critical": 25, "high": 10, "medium": 4, "info": 0}


def spec_type(t):
    """Resolve a @type to the SPEC key it is validated against (or None)."""
    if t in SPEC:
        return t
    parent = SUBTYPES.get(t)
    return parent if parent in SPEC else None


def _first_type(obj):
    t = obj.get("@type")
    if isinstance(t, list):
        t = t[0] if t else None
    return t if isinstance(t, str) else None


def _empty(v):
    return v in (None, "", [], {})


def _is_ref(v):
    return isinstance(v, dict) and set(v) == {"@id"}


def _as_list(v):
    return v if isinstance(v, list) else [v]


def _abs_url(v):
    return isinstance(v, str) and re.match(r"^https?://[^/\s]+", v) is not None


# --- value checks -------------------------------------------------------------------------

def _value_issues(t, obj, add):
    for p in DATE_PROPS & set(obj):
        v = obj[p]
        if isinstance(v, str) and not ISO_DATE.match(v.strip()):
            add("medium", p, f'{p} "{v}" is not ISO 8601',
                "Use YYYY-MM-DD or a full timestamp with timezone, e.g. 2026-09-25T09:00:00+00:00.")
    dp, dm = obj.get("datePublished"), obj.get("dateModified")
    if isinstance(dp, str) and isinstance(dm, str) and ISO_DATE.match(dp) and ISO_DATE.match(dm) \
            and dm[:10] < dp[:10]:
        add("medium", "dateModified", "dateModified is earlier than datePublished",
            "Set dateModified to the last real content change (>= datePublished).")
    for p in URL_PROPS & set(obj):
        for v in _as_list(obj[p]):
            if isinstance(v, str) and v and not _abs_url(v) and not v.startswith("data:"):
                add("medium", p, f'{p} "{v[:60]}" is not an absolute URL',
                    "Use absolute https:// URLs in structured data.")
    ctx = obj.get("@context")
    if isinstance(ctx, str) and "schema.org" not in ctx:
        add("high", "@context", f'@context "{ctx}" is not schema.org',
            'Set "@context": "https://schema.org".')
    if t in ("Offer", "AggregateOffer"):
        for p in ("price", "lowPrice", "highPrice"):
            if p in obj:
                v = obj[p]
                if isinstance(v, str) and not re.match(r"^\d+(\.\d+)?$", v.strip()):
                    add("high", p, f'{p} "{v}" is not a plain number',
                        "Use digits and a dot only (e.g. 49.99); no currency symbols or commas.")
        cur = obj.get("priceCurrency")
        if isinstance(cur, str) and not re.match(r"^[A-Z]{3}$", cur):
            add("high", "priceCurrency", f'priceCurrency "{cur}" is not ISO 4217',
                "Use a three-letter code such as USD or EUR.")
        av = obj.get("availability")
        if isinstance(av, str) and av.rsplit("/", 1)[-1] not in AVAILABILITY:
            add("medium", "availability", f'availability "{av}" is not a schema.org value',
                "Use https://schema.org/InStock (or OutOfStock, PreOrder, BackOrder, ...).")
        ic = obj.get("itemCondition")
        if isinstance(ic, str) and ic.rsplit("/", 1)[-1] not in CONDITION:
            add("medium", "itemCondition", f'itemCondition "{ic}" is not a schema.org value',
                "Use https://schema.org/NewCondition (or Used/Refurbished/Damaged).")
    if t == "AggregateRating":
        try:
            rv = float(obj.get("ratingValue"))
            best = float(obj.get("bestRating", 5))
            worst = float(obj.get("worstRating", 1))
            if not (worst <= rv <= best):
                add("high", "ratingValue", f"ratingValue {rv:g} outside {worst:g}..{best:g}",
                    "Set bestRating/worstRating to match the scale the rating uses.")
        except (TypeError, ValueError):
            if "ratingValue" in obj:
                add("high", "ratingValue", "ratingValue is not numeric", "Use a number, e.g. 4.6.")
        for p in ("ratingCount", "reviewCount"):
            if p in obj:
                try:
                    if int(str(obj[p])) <= 0:
                        raise ValueError
                except ValueError:
                    add("high", p, f"{p} must be a positive integer",
                        "Only mark up ratings backed by real, visible reviews.")
    if t == "BreadcrumbList":
        items = [i for i in _as_list(obj.get("itemListElement")) if isinstance(i, dict)]
        pos = [i.get("position") for i in items]
        try:
            if [int(p) for p in pos] != list(range(1, len(items) + 1)):
                raise ValueError
        except (TypeError, ValueError):
            add("medium", "itemListElement", "breadcrumb positions are not 1..N in order",
                "Number ListItem.position 1, 2, 3 ... in trail order.")
        for i in items[:-1]:
            if not i.get("item"):
                add("medium", "itemListElement", f'breadcrumb "{i.get("name", "?")}" has no item URL',
                    "Every crumb except the last needs an item URL.")
    if t == "Article":
        a = obj.get("author")
        if isinstance(a, str):
            add("info", "author", "author is a plain string",
                "Use a Person/Organization with name + url (or an @id to a ProfilePage entity).")


# --- validation ---------------------------------------------------------------------------

def validate_obj(obj, nested_in=None, _depth=0):
    """Validate one JSON-LD node. Returns a findings dict (back-compatible keys
    type/missing_required/missing_recommended/warnings/ok, plus `issues` records)."""
    findings = {"type": None, "missing_required": [], "missing_recommended": [],
                "warnings": [], "issues": [], "ok": False}
    t = _first_type(obj)
    findings["type"] = t

    def add(sev, prop, finding, fix):
        findings["issues"].append({"type": t, "severity": sev, "property": prop,
                                   "finding": finding, "fix": fix})
        if sev in ("medium", "high", "critical") and prop not in findings["missing_required"]:
            findings["warnings"].append(finding)

    if not obj.get("@context") and nested_in is None:
        findings["warnings"].append('missing "@context" (should be "https://schema.org")')
        findings["issues"].append({"type": t, "severity": "high", "property": "@context",
                                   "finding": 'missing "@context"',
                                   "fix": 'Add "@context": "https://schema.org".'})
    key = spec_type(t)
    if key is None:
        findings["warnings"].append(f'no required-property spec for type "{t}" (validated context only)')
        findings["issues"].append({"type": t, "severity": "info", "property": "@type",
                                   "finding": f'no spec for "{t}" (context/values checked only)',
                                   "fix": ""})
        _value_issues(t, obj, add)
        findings["ok"] = not any(i["severity"] in ("critical", "high") for i in findings["issues"])
        return findings
    spec = SPEC[key]
    skip = set(spec.get("nested_skip", [])) if nested_in else set()
    for p in spec["required"]:
        if p in skip:
            continue
        if p not in obj or _empty(obj.get(p)):
            findings["missing_required"].append(p)
            findings["issues"].append({"type": t, "severity": "high", "property": p,
                                       "finding": f"{t}: missing required {p}",
                                       "fix": f"Add {p} (it must also be visible on the page)."})
    for group in spec.get("required_any", []):
        if not any(g in obj and not _empty(obj[g]) for g in group):
            label = " or ".join(group)
            findings["missing_required"].append(label)
            findings["issues"].append({"type": t, "severity": "high", "property": label,
                                       "finding": f"{t}: needs at least one of {label}",
                                       "fix": f"Add {group[0]} (or another of: {label})."})
    for p in spec.get("recommended", []):
        if p not in obj:
            findings["missing_recommended"].append(p)
    if findings["missing_recommended"]:
        findings["issues"].append({"type": t, "severity": "info", "property": "recommended",
                                   "finding": f"{t}: recommended not set: "
                                              + ", ".join(findings["missing_recommended"]),
                                   "fix": "Add them when the data exists on the page."})
    if spec.get("deprecated_rich"):
        findings["warnings"].append("DEPRECATED rich result: " + spec.get("notes", ""))
        findings["issues"].append({"type": t, "severity": "info", "property": "@type",
                                   "finding": "retired rich result: " + spec.get("notes", ""),
                                   "fix": "Keep the markup if accurate; do not promise a rich result."})
    elif spec.get("notes"):
        findings["warnings"].append(spec["notes"])
    _value_issues(key, obj, add)

    # nested typed values validated against their own spec (bounded depth)
    if _depth < 4:
        for prop, ntype in spec.get("nested", {}).items():
            for v in _as_list(obj.get(prop)):
                if isinstance(v, dict) and not _is_ref(v):
                    vt = _first_type(v)
                    if vt is None:
                        v = dict(v, **{"@type": ntype})
                    sub = validate_obj(v, nested_in=t, _depth=_depth + 1)
                    for i in sub["issues"]:
                        i = dict(i, property=f"{prop}.{i['property']}")
                        findings["issues"].append(i)
                        if i["severity"] in ("critical", "high"):
                            findings["missing_required"].append(i["property"])
    findings["ok"] = not any(i["severity"] in ("critical", "high") for i in findings["issues"])
    return findings


def top_nodes(doc):
    """Top-level nodes of a JSON-LD document (a node, a list, or an @graph wrapper).
    The wrapper's @context is propagated so graph members aren't flagged context-less."""
    out = []
    for d in _as_list(doc):
        if not isinstance(d, dict):
            continue
        if "@graph" in d:
            ctx = d.get("@context")
            for n in _as_list(d["@graph"]):
                if isinstance(n, dict):
                    out.append(dict({"@context": ctx}, **n) if ctx and "@context" not in n else n)
        else:
            out.append(d)
    return out


def validate_doc(doc):
    results = [validate_obj(n) for n in top_nodes(doc)]
    return results


def score(issues):
    return max(0, 100 - sum(PENALTY[i["severity"]] for i in issues))


def generate(type_name, data):
    obj = {"@context": "https://schema.org", "@type": type_name}
    obj.update(data)
    return obj


# --- HTML extraction ----------------------------------------------------------------------

LD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                   re.I | re.S)


def extract_jsonld(html):
    """Return (docs, errors) for every ld+json block in an HTML string."""
    docs, errors = [], []
    for i, block in enumerate(LD_RE.findall(html), 1):
        try:
            docs.append(json.loads(block))
        except ValueError as e:
            errors.append(f"block {i}: invalid JSON ({e})")
    return docs, errors


def _load_source(path):
    """(docs, errors) from an .html/.htm file or a JSON(-LD) file."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if path.lower().endswith((".html", ".htm")) or LD_RE.search(text):
        return extract_jsonld(text)
    try:
        return [json.loads(text)], []
    except ValueError as e:
        return [], [f"invalid JSON ({e})"]


# --- cross-page @id graph ----------------------------------------------------------------

def _walk(node, fn, depth=0):
    if depth > 12:
        return
    if isinstance(node, dict):
        fn(node)
        for k, v in node.items():
            if k != "@context":
                _walk(v, fn, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _walk(v, fn, depth + 1)


def graph_check(sources):
    """sources: {label: [docs]}. Returns the entity-graph report."""
    defined, refs, issues = {}, [], []
    orgs, sites, nodes = set(), set(), 0

    for label, docs in sources.items():
        def visit(n, label=label):
            nonlocal nodes
            if _is_ref(n):
                refs.append((label, n["@id"]))
                return
            t = _first_type(n)
            if t:
                nodes += 1
            if "@id" in n and t:
                defined.setdefault(n["@id"], []).append((label, t))
            key = spec_type(t) if t else None
            if key in ORG_TYPES:
                orgs.add(n.get("@id") or "(no @id on %s)" % label)
            if t == "WebSite":
                sites.add(n.get("@id") or "(no @id on %s)" % label)
        for d in docs:
            _walk(d, visit)

    unresolved = sorted({i for _, i in refs if i not in defined})
    for i in unresolved:
        where = sorted({lab for lab, x in refs if x == i})
        issues.append({"severity": "high", "finding": f"dangling @id reference {i}",
                       "where": where,
                       "fix": "Define that node (with its @type) on this page or a page in "
                              "the set, or correct the @id spelling."})
    for i, defs in sorted(defined.items()):
        types = sorted({t for _, t in defs})
        if len(types) > 1:
            issues.append({"severity": "medium",
                           "finding": f"@id {i} defined with conflicting types {types}",
                           "where": sorted({lab for lab, _ in defs}),
                           "fix": "One @id = one entity = one @type everywhere."})
        if not re.match(r"^https?://", i):
            issues.append({"severity": "info", "finding": f"@id {i} is not an absolute URL",
                           "where": sorted({lab for lab, _ in defs}),
                           "fix": "Use https://site/#fragment ids so they are globally unique."})
    if not orgs:
        issues.append({"severity": "medium", "finding": "no Organization (or LocalBusiness) entity",
                       "where": [], "fix": "Add one Organization node with a stable @id and "
                                           "reference it as publisher/about from every page."})
    elif len(orgs) > 1:
        issues.append({"severity": "medium",
                       "finding": f"entity split: {len(orgs)} distinct Organization ids {sorted(orgs)}",
                       "where": [], "fix": "Use the same Organization @id on every page."})
    if not sites:
        issues.append({"severity": "info", "finding": "no WebSite entity",
                       "where": [], "fix": "Add a WebSite node (name, url, publisher -> Organization @id)."})
    return {"sources": len(sources), "nodes": nodes, "ids_defined": len(defined),
            "references": len(refs), "unresolved": unresolved, "issues": issues,
            "ok": not any(i["severity"] in ("critical", "high") for i in issues),
            "score": score(issues)}


# --- site graph starter ------------------------------------------------------------------

def site_graph(cfg):
    """Linked Organization + WebSite + WebPage (+ BreadcrumbList) @graph."""
    base = cfg["url"].rstrip("/")
    org_id, site_id = base + "/#organization", base + "/#website"
    org = {"@type": cfg.get("orgType", "Organization"), "@id": org_id,
           "name": cfg["name"], "url": base + "/"}
    for k in ("logo", "sameAs", "description", "telephone", "address"):
        if cfg.get(k):
            org[k] = cfg[k]
    graph = [org, {"@type": "WebSite", "@id": site_id, "name": cfg.get("siteName", cfg["name"]),
                   "url": base + "/", "publisher": {"@id": org_id}}]
    page = cfg.get("page")
    if page:
        purl = page["url"]
        node = {"@type": page.get("type", "WebPage"), "@id": purl + "#webpage",
                "url": purl, "name": page["name"], "isPartOf": {"@id": site_id},
                "about": {"@id": org_id}}
        crumbs = page.get("breadcrumb") or []
        if crumbs:
            node["breadcrumb"] = {"@id": purl + "#breadcrumb"}
        graph.append(node)
        if crumbs:
            graph.append({"@type": "BreadcrumbList", "@id": purl + "#breadcrumb",
                          "itemListElement": [
                              dict({"@type": "ListItem", "position": n, "name": c[0]},
                                   **({"item": c[1]} if len(c) > 1 and c[1] else {}))
                              for n, c in enumerate(crumbs, 1)]})
    return {"@context": "https://schema.org", "@graph": graph}


# --- CLI ------------------------------------------------------------------------------------

def _load_jsonld(arg):
    """arg may be a path to a .json file or an inline JSON string."""
    if os.path.exists(arg):
        with open(arg, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)


def _summary(results, errors=()):
    issues = [i for r in results for i in r["issues"]]
    issues += [{"type": None, "severity": "high", "property": "json",
                "finding": e, "fix": "Fix the JSON syntax; the whole block is ignored."}
               for e in errors]
    return {"validated": len(results), "results": results,
            "detected": sorted({r["type"] for r in results if r["type"]}),
            "deprecations": sorted({r["type"] for r in results
                                    if SPEC.get(spec_type(r["type"]) or "", {}).get("deprecated_rich")}),
            "errors": list(errors), "score": score(issues),
            "ok": all(r["ok"] for r in results) and not errors}


def _human(out):
    if "jsonld" in out:
        print(json.dumps(out["jsonld"], indent=2))
        out = {"results": [out["validation"]], "score": score(out["validation"]["issues"])}
    if "results" in out:
        print(f"-- validation: {len(out['results'])} node(s), score {out.get('score')}/100 --")
        for r in out["results"]:
            print(f"{r['type']}: {'OK' if r['ok'] else 'NOT ELIGIBLE'}")
            for i in r["issues"]:
                if i["severity"] != "info" or "retired" in i["finding"]:
                    print(f"  [{i['severity'].upper()}] {i['finding']}"
                          + (f"  -> {i['fix']}" if i["fix"] else ""))
        for e in out.get("errors", []):
            print(f"  [HIGH] {e}")
    if "unresolved" in out:
        print(f"-- entity graph: {out['nodes']} nodes, {out['ids_defined']} @ids, "
              f"{out['references']} refs, score {out['score']}/100 --")
        for i in out["issues"]:
            print(f"  [{i['severity'].upper()}] {i['finding']} -> {i['fix']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", help="Schema type to generate (see --list)")
    ap.add_argument("--data", default="{}", help="JSON object of properties")
    ap.add_argument("--validate", help="path or inline JSON-LD to validate")
    ap.add_argument("--html", nargs="+", help="HTML file(s): extract + validate ld+json")
    ap.add_argument("--graph", "--graph-check", nargs="+", dest="graph",
                    help="HTML/JSON files: cross-page @id entity-graph check")
    ap.add_argument("--site", help="JSON config (path or inline) for a linked site @graph starter")
    ap.add_argument("--list", action="store_true", help="list known types + required props")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args(argv)

    if args.list:
        for t, s in SPEC.items():
            dep = (" [rich-result DEPRECATED]" if s.get("deprecated_rich")
                   else " [no rich result]" if s.get("rich") is False else "")
            print(f"{t}{dep}: required={s['required']} "
                  f"any_of={s.get('required_any', [])} recommended={s.get('recommended', [])}")
        return 0

    if args.validate:
        try:
            doc = _load_jsonld(args.validate)
        except (json.JSONDecodeError, OSError) as e:
            print(json.dumps({"error": f"could not parse JSON-LD: {e}"}))
            return 1
        out = _summary(validate_doc(doc))
    elif args.html:
        results, errors = [], []
        for p in args.html:
            try:
                docs, errs = _load_source(p)
            except OSError as e:
                print(json.dumps({"error": f"could not read {p}: {e}"}))
                return 1
            for d in docs:
                results += validate_doc(d)
            errors += [f"{os.path.basename(p)} {e}" for e in errs]
        out = _summary(results, errors)
        if not results and not errors:
            out["errors"] = ["no application/ld+json blocks found"]
            out["ok"] = False
    elif args.graph:
        sources = {}
        for p in args.graph:
            try:
                docs, _ = _load_source(p)
            except OSError as e:
                print(json.dumps({"error": f"could not read {p}: {e}"}))
                return 1
            sources[os.path.basename(p)] = docs
        out = graph_check(sources)
    elif args.site:
        try:
            cfg = _load_jsonld(args.site)
            doc = site_graph(cfg)
        except (json.JSONDecodeError, OSError, KeyError, AttributeError, TypeError) as e:
            print(json.dumps({"error": f"--site needs JSON with name + url ({e})"}))
            return 1
        out = {"jsonld": doc, "validation": _summary(validate_doc(doc)),
               "graph": graph_check({"site": [doc]})}
        if args.human:
            print(json.dumps(doc, indent=2))
            _human(out["validation"])
            _human(out["graph"])
            return 0
    elif args.type:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"--data is not valid JSON: {e}"}))
            return 1
        obj = generate(args.type, data)
        out = {"jsonld": obj, "validation": validate_obj(obj)}
    else:
        print("Specify --type, --validate, --html, --graph, --site, or --list.", file=sys.stderr)
        return 2

    if args.human:
        _human(out)
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
