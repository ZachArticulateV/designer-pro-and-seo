---
name: seo-image-audit
description: Audit a page's images for SEO and performance — alt-text quality (missing, linked-empty, filename, stuffed, reused), modern formats (WebP/AVIF), responsive srcset/sizes, LCP loading (lazy hero, fetchpriority), CLS-safe dimensions, real byte and pixel budgets read from the image files, and og:image — scored, with ready-to-run conversion commands. Uses DataForSEO for live image-SERP rankings when connected; otherwise audits from page fetch and parsing alone. Trigger when the user says "image seo", "image audit", "alt text", "image optimization", "convert to webp", "convert to avif", or "image performance".
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

1. **Run the image audit** — on a live page (fetched through the shared SSRF guard) or
   a local build, where `--assets` lets it read real file bytes and pixel dimensions
   from the image headers:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/image_audit.py" --url <URL> --human
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/image_audit.py" --file page.html --url <URL> --assets dist/ --human
   ```
   Findings by type, each listing the affected images (codes, budgets and scoring:
   `references/seo-image-audit/image-rubric.md`):
   - **Alt** — missing, empty on a linked image (the link loses its name), file name
     as alt, "image of…", over-long, keyword-stuffed, reused across images.
   - **Format** — legacy JPEG/PNG/GIF with no WebP/AVIF alternative.
   - **Responsive** — no `srcset`/`<picture>`; `srcset` without `sizes`.
   - **Loading** — lazy-loaded hero (LCP), several or no `fetchpriority=high`,
     below-the-fold images not lazy.
   - **CLS** — no width+height or `aspect-ratio`.
   - **Size** (`--assets`) — over 500 KB, over the 200 KB hero / 250 KB budget,
     intrinsic pixels > 2.5× the declared width, declared ratio ≠ file ratio. Without
     `--assets` these are listed under `needs_data`, never guessed.
   - **Filename / social** — camera or hash file names; missing or relative `og:image`.
2. **Judge alt text in context** — the script catches the mechanical failures; read the
   remaining alts against what each image shows on *this* page.
3. **Optional enrichment** — if the DataForSEO extension is configured, add image
   SERP rankings; otherwise state, in one line, what it would add.
4. **Deliver** the findings with fixes, the biggest byte/pixel wins first, and the
   emitted `conversions` (ready-to-run `cwebp` / `avifenc` / ImageMagick commands per
   legacy image) — the script prints them; running them needs those tools installed.

## Outputs

- Findings by type with affected images, fixes, and a 0-100 score
- A summary of the biggest performance wins (format + size)
- A short "what paid data would add" note on the free path

## Dependencies

- `scripts/seo/image_audit.py` (required) — the image audit (stdlib header parsing)
- `references/seo-image-audit/image-rubric.md` (required) — codes, budgets, scoring
- Optional: DataForSEO extension (image SERP); `seo-page` (page-level context)

## Notes

Pairs with `seo-image-gen` (the generation half). Actual file conversion
(WebP/AVIF) and metadata injection require Sharp/ImageMagick if you want the skill
to perform the conversion rather than recommend it.
