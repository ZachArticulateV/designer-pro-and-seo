---
template: dimensions-template
used_by: [design-dimensions]
purpose: 5-dimension design brief; forces Motion (the most-skipped dimension) to be explicit.
---

# DESIGN BRIEF (5 Dimensions) — {{target}}

> All five must have substantive content before the brief is "done". Dimensions
> 1–4 can be pulled from a `design-system-gen` result; dimension 5 (Motion) is the
> one that gets skipped — fill it deliberately.

## 1. Pattern & Layout (the skeleton)
- Page/section structure: {{structure}}
- Section sequence (top → bottom): {{sequence}}
- Hierarchy & density: {{hierarchy}}
- Responsive behavior (mobile → desktop): {{responsive}}

## 2. Style & Aesthetic (the skin)
- Style: {{style}}
- Surface treatment (borders, fills, depth): {{surfaces}}
- Imagery direction (photo / illustration / abstract): {{imagery}}
- Reference touchstones (describe, don't copy): {{references}}

## 3. Color & Theme (the palette)
- Primary {{primary}} · Secondary {{secondary}} · Accent {{accent}}
- Background {{bg}} · Surface {{surface}} · Text {{text}}
- Semantic: success {{success}} · warning {{warning}} · error {{error}}
- Light/dark: {{theme_modes}}
- Contrast check: body text ≥ 4.5:1 confirmed? {{contrast_ok}}

## 4. Typography (the voice)
- Heading: {{heading_font}} @ {{heading_weight}}
- Body: {{body_font}} @ {{body_weight}}
- Type scale: {{scale}}
- Tracking / leading notes: {{tracking}}

## 5. Motion & Interaction (the life)  ← do not skip
- Animation curve & base duration: {{motion}}
- Entrance/scroll behaviors: {{scroll_motion}}
- Micro-interactions (hover, press, focus): {{micro}}
- Page/section transitions: {{transitions}}
- Reduced-motion fallback: {{reduced_motion}}  <!-- required for accessibility -->

---
### Completeness gate
- [ ] Pattern & Layout
- [ ] Style & Aesthetic
- [ ] Color & Theme (contrast checked)
- [ ] Typography
- [ ] Motion & Interaction (incl. reduced-motion fallback)
