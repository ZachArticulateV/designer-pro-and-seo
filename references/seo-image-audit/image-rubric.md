# seo-image-audit — Image Rubric, Budgets & Scoring

The durable knowledge behind `scripts/seo/image_audit.py`. Knowledge, not steps.
Core Web Vitals context is in `references/shared/cwv-thresholds.md`, and alt text as
an accessibility requirement is in `references/shared/wcag-contrast-rules.md` and the
`design-accessibility` references.

## Why images are an SEO and a performance problem at once

The hero image is the LCP element on most pages. Images without reserved space are the
most common cause of CLS. Images are also a ranking surface in their own right (Google
Images, visual answers, share previews). Alt text serves three readers: screen-reader
users, crawlers, and AI answer engines that describe the page. The same attributes
decide all of it, so one pass audits both sides.

## Finding codes

| Code | Check | Severity |
|---|---|---|
| A1 | image missing `alt` | high |
| A2 | decorative image (`role=presentation` / `aria-hidden`) without `alt=""` | medium |
| A3 | linked image with empty alt and no link text, so the link has no accessible name | high |
| A4 | alt is just the file name | medium |
| A5 | alt starts "image of…" / "picture of…" | info |
| A6 | alt over 125 characters | medium |
| A7 | alt looks keyword-stuffed (3+ commas in a short alt, or a word 3+ times) | medium |
| A8 | one alt reused on different images | medium |
| F1 | legacy JPEG/PNG/GIF/BMP/TIFF with no WebP/AVIF alternative | medium |
| R1 | content image without `srcset` or `<picture>` | medium |
| R2 | `srcset` with w-descriptors but no `sizes` (browser assumes 100vw) | medium |
| L1 | first content image lazy-loaded (likely LCP) | high |
| L2 | several `fetchpriority=high` | medium |
| L3 | no `fetchpriority=high` | info |
| L4 | 3+ images past the first two, none lazy-loaded | medium |
| C1 | no width+height and no CSS `aspect-ratio` | medium |
| S1 | file over 500 KB | high |
| S2 | over budget: 200 KB for the hero, 250 KB for other images | medium |
| S3 | intrinsic width over 2.5× the declared width, with no `srcset` | medium |
| S4 | declared aspect ratio differs from the file by over 5% | medium |
| N1 | camera / hash / generic file name | info |
| O1 | no `og:image` | medium |
| O2 | `og:image` not absolute | medium |

"Content images" exclude SVGs and anything declared under 64 px wide (icons, logos).
Those still get alt checks.

## What needs real data

S1–S4 need the actual files. With `--assets BUILD_DIR` the script resolves each `src`
against the build (path traversal outside the directory is refused). It reads bytes
and **intrinsic pixel dimensions straight from the file headers**, all in stdlib: PNG
IHDR, GIF logical screen, JPEG SOF, WebP VP8/VP8L/VP8X, and AVIF `ispe`. Without
`--assets`, those checks are listed under `needs_data` rather than guessed.

The audit parses HTML, so it doesn't see CSS background images or images injected by
JavaScript. Audit those in the rendered page.

## Targets that hold up

- **Format:** AVIF first, WebP fallback, via `<picture>` or CDN content negotiation.
  Quality around 60–80 is visually lossless for photos. Keep PNG for flat graphics
  only when WebP-lossless isn't smaller. The script emits `cwebp`, `avifenc` and
  ImageMagick commands for every F1 image. It never converts files itself.
- **Pixels:** serve about 2× the rendered CSS width at most, and let `srcset` + `sizes`
  pick. A 2400 px file rendered at 800 px is 9× the pixels a 1× screen needs.
- **Loading:** the LCP image is eager with `fetchpriority="high"` and never lazy. Every
  image below the first viewport is `loading="lazy"` with `decoding="async"`.
- **Alt:** describe what the image shows, *in the context of the page*, in under
  about 125 characters. Mention the topic once only where it is genuinely what is
  pictured. Use `alt=""` for decoration. A linked image's alt describes the destination.
- **File names:** name files for their content before upload (`cedar-garden-bench.avif`),
  because it is the first description a crawler sees.

## Scoring

`score = max(0, 100 − 25·critical − 10·high − 4·medium)` **per finding type**. Each
finding lists the affected images and a `count`, so fifty unoptimized images cost one
F1. The number ranks pages for triage. The image list is the work order.

## Worked example (pinned by `tests/test_image_audit.py`)

`references/examples/seo-image-audit/page.html` with `--assets` scores **48/100**.

- **2 high (−20):**
  - A3: the porch-swing card link has no name
  - L1: the hero is lazy-loaded
- **8 medium (−32):**
  - A4: `IMG_4821` as alt
  - A7: stuffed alt on the grain photo
  - C1: two images without dimensions
  - F1: four PNG/JPEG files with no modern format
  - O1: no `og:image`
  - R1: no `srcset` on four images
  - S3: a 2400 px hero declared at 800 px
  - S4: an 800×600 file declared 400×400

The info findings (L3, N1) cost nothing.
