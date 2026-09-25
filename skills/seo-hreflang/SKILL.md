---
name: seo-hreflang
description: Validates and generates hreflang annotations for international SEO. Checks language/region codes, self-reference, x-default, duplicates, and absolute URLs, and flags return-link reciprocity to verify; generates HTML alternate link tags and identifies HTTP Link header and XML sitemap placement. Trigger when the user says "hreflang", "i18n SEO", "international SEO", "multi-language", "multi-region", "language tags", or "regional SEO".
---

# seo-hreflang

**Family:** seo
**Status:** Stable

## Purpose

Hreflang is one of the most-misimplemented SEO patterns. This skill validates and
generates correct annotations and catches the mistakes that quietly break
international ranking: invalid codes, missing self-reference, missing x-default,
duplicates, and non-reciprocal return links.

Three valid signal locations: HTML `<link rel="alternate" hreflang>`, the HTTP
`Link:` header, and XML sitemap `xhtml:link` entries.

## Triggers

- "hreflang" / "i18n seo" / "international seo"
- "multi-language" / "multi-region" / "language tags" / "regional seo"

## Inputs

- Mode: validate | generate
- Validate: the page's hreflang set (list of {hreflang, href}) + the page's own URL
- Generate: a locale→URL map (+ optional x-default URL)

## Steps

1. **Audit the whole cluster** (the step that matters — hreflang only works when every
   page lists every page, itself included, and every link is returned):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/hreflang_tools.py" --cluster manifest.json   # {"https://site.com/": "en.html", ...}
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/hreflang_tools.py" --cluster en.html fr.html de.html   # URLs from each page's canonical
   ```
   Checks H1–H12: missing annotations, invalid codes (with fixes for `en-uk`, `jp`,
   `es-419` …), self-reference, x-default presence and consistency, absolute hrefs,
   **return links**, one code per URL, `<html lang>` agreement, and alternates that are
   noindex or canonicalized elsewhere (`references/seo-hreflang/cluster-rules.md`).
2. **Validate one page's set** when only a single page is available:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/hreflang_tools.py" --validate cluster.json --self <this-page-url>
   ```
3. **Generate** a correct set:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/hreflang_tools.py" --generate --map locales.json --x-default https://site.com/
   ```
   Emits the `<link rel="alternate">` tags to place on **every** alternate page, or to
   deliver via the `Link:` header / sitemap (sitemap alternates are checked by
   `sitemap_tools.py --validate`, codes S25/S26).
4. **Render** the findings by severity with fixes, or the generated blocks.

## Outputs

- Cluster report (codes, self-reference, return links, x-default, lang, noindex/canonical) with a score
- Single-set validation report
- Generated hreflang blocks for the chosen delivery method

## Dependencies

- `scripts/seo/hreflang_tools.py` (required) — Python 3.10+, standard library only
- `references/seo-hreflang/cluster-rules.md` (required) — code rules, cluster checks, scoring

## Notes

Conditional in `seo-audit` — only fires when multi-locale signals are present.
Don't audit hreflang on single-locale sites.
