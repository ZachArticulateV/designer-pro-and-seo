# Golden example — design-motion (`motion_audit.py`)

`styles.css` is a first-draft motion layer (fictional brand) and `page.html` has an
autoplaying loop video.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/design/motion_audit.py" \
  --css references/examples/design-motion/styles.css \
  --html references/examples/design-motion/page.html --human
```

**Expected result: score 60/100.**

- **High:**
  - M1: 5 animated rules and no reduced-motion query. The fix prints the guard block.
  - M8: `.btn:focus { outline: none }` with no `:focus-visible` replacement.
- **Medium:**
  - M2: `height`, `max-height` and `@keyframes slide-in` on `left`
  - M3: `transition: all`
  - M4: a 1200 ms accordion
  - M5: an infinite pulse
  - M6: an autoplay loop without muted + controls
- **Info:** M7, smooth scrolling not reset.

Add the guard block from `references/design-motion/motion-rubric.md` and a
`:focus-visible` ring, and both high findings clear. `tests/test_design_qa.py` pins
the result.
