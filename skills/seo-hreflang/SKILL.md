---
name: seo-hreflang
description: International SEO — hreflang validation and generation across HTML, HTTP header, and sitemap implementations. Validates language/region codes, self-reference, x-default, and flags return-link reciprocity to verify. Trigger when the user says "hreflang", "i18n SEO", "international SEO", "multi-language", "multi-region", "language tags", or "regional SEO".
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

1. **Validate an existing set:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/hreflang_tools.py" --validate cluster.json --self <this-page-url>
   ```
   Checks ISO 639-1 language + ISO 3166-1 region codes, self-reference presence,
   x-default, duplicates, and absolute URLs; flags reciprocity to verify per-page.
2. **Generate** a correct set:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/hreflang_tools.py" --generate --map locales.json --x-default https://site.com/
   ```
   Emits the `<link rel="alternate">` tags to place on **every** alternate page
   (including a self-reference), or to return via the `Link:` header / sitemap.
3. **Reciprocity** — remind the user that A→B requires B→A; for a full cluster,
   capture each page's set and cross-check (needs per-page fetch).
4. **Render** the audit (violations by severity) or the generated blocks.

## Outputs

- Validation report (code/self/x-default/duplicate/reciprocity issues)
- Generated hreflang blocks for the chosen delivery method

## Dependencies

- `scripts/seo/hreflang_tools.py` (required) — Python 3.10+, standard library only

## Notes

Conditional in `seo-audit` — only fires when multi-locale signals are present.
Don't audit hreflang on single-locale sites.
