---
name: seo-image-audit
description: Audit a page's images for SEO and performance — alt text, file size, modern formats (WebP/AVIF), responsive srcset, lazy loading, CLS prevention, and optional image SERP rankings. Trigger when the user says "image seo", "alt text", "image optimization", "image audit", "convert to webp", "image metadata", or "image rankings".
---

# seo-image-audit

**Family:** seo
**Status:** Stable

## Purpose

The audit half of image SEO (split from generation because the two have different
legal, asset, and API risk). Inventories a page's images and scores each on the
dimensions that affect search and performance. The free path (fetch + parse) is
the whole product; DataForSEO only adds live image-SERP context.

## Triggers

- "image seo" / "image audit" / "image optimization"
- "alt text" / "image metadata"
- "convert to webp" / "convert to avif"
- "image rankings" / "google images"

## Inputs

- Page URL or local HTML/build path (or an image directory)
- Optional: target keyword(s) for alt-text relevance

## Steps

1. **Inventory images** — fetch the page (or scan the directory) and list every
   image with its `src`, dimensions, format, and file size.
2. **Score each image:**
   - **Alt text** — present? descriptive? keyword-relevant without stuffing?
     (decorative images should have empty `alt=""`).
   - **Format** — modern (WebP/AVIF) vs legacy (JPEG/PNG); flag conversion wins.
   - **File size / dimensions** — oversized for display size? recommend target.
   - **Responsive** — `srcset`/`sizes`/`<picture>` present where useful?
   - **Lazy loading** — `loading="lazy"` below the fold; eager for the LCP image.
   - **CLS** — width/height or aspect-ratio declared to reserve space?
3. **Optional enrichment** — if the DataForSEO extension is configured, add image
   SERP rankings; otherwise state, in one line, what it would add.
4. **Render findings** grouped Critical / High / Medium / Low, each with a concrete
   fix and (for format/size) the recommended target. For "convert to webp/avif"
   requests, output ready-to-run conversion commands per image (`cwebp`, ImageMagick
   `magick`, or a Sharp snippet) as the actionable deliverable — running them needs
   that tool installed (see Notes).

## Outputs

- Per-image findings table with prioritized fixes
- A summary of the biggest performance wins (format + size)
- A short "what paid data would add" note on the free path

## Dependencies

- None required — the free path uses page fetch + parsing
- Optional: DataForSEO extension (image SERP); `seo-page` (page-level context)

## Notes

Pairs with `seo-image-gen` (the generation half). Actual file conversion
(WebP/AVIF) and metadata injection require Sharp/ImageMagick if you want the skill
to perform the conversion rather than recommend it.
