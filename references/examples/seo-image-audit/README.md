# Golden example — seo-image-audit (Tier-2: `image_audit.py`)

Proves the free, offline image audit, including real byte and pixel checks. The
script reads PNG, GIF, JPEG, WebP and AVIF headers with the Python standard library,
so there's nothing to install.

## Input

- `page.html`: a product page (fictional brand) with five images:
  - a lazy-loaded hero declared 800×450 whose file is 2400×1350
  - `IMG_4821` used as alt text on an 800×600 file declared 400×400
  - a keyword-stuffed alt
  - an image-only link with `alt=""` (so the link has no name)
  - an SVG logo
  It has no `og:image`.
- `assets/img/`: the three PNGs the page references, generated solid-color files with
  real headers. `porch-swing.jpg` is intentionally absent.

## Command

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seo/image_audit.py" \
  --file references/examples/seo-image-audit/page.html \
  --url https://example.test/benches/classic \
  --assets references/examples/seo-image-audit/assets --human
```

## Expected free deliverable (Tier 2)

`5 images (4 content)  score 48/100`, then:

- **High:**
  - `A3`: the linked image has an empty alt, so the link has no name
  - `L1`: the hero is lazy-loaded
- **Medium:**
  - `A4`: filename used as alt
  - `A7`: stuffed alt
  - `C1`: ×2 images without dimensions
  - `F1`: ×4 legacy formats
  - `O1`: no og:image
  - `R1`: ×4 images without srcset
  - `S3`: 2400 px hero declared at 800 px
  - `S4`: 800×600 file declared 400×400
- **Info:**
  - `L3`: no fetchpriority=high
  - `N1`: `IMG_4821` is a camera file name
- **Conversions:** `cwebp` / `avifenc` / `magick` commands for the four legacy images.

The SVG logo is excluded from content-image checks. Without `--assets`, the S-codes
move to `needs_data` instead of being guessed. `tests/test_image_audit.py` pins the
score and the code set.
