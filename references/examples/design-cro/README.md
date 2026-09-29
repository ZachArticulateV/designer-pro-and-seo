# Golden example — design-cro (`cro_audit.py`)

`landing.html` is a custom-order landing page (fictional brand) with the usual
conversion leaks:
- a "Welcome to…" headline
- four competing buttons before the first section
- "Learn more" and "Submit" labels
- a 9-field quote form that requires phone and company
- a phone number that isn't tap-to-call
- no value copy under the headline

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/design/cro_audit.py" --file references/examples/design-cro/landing.html --human
```

**Expected result: score 60/100.** Findings in leverage order (impact ÷ effort), each
citing its `data/ux-rules.csv` rule where one exists:

1. K10: generic headline
2. K3: 4 competing CTAs
3. K4: generic labels
4. K6: phone and company required
5. K9: not tap-to-call
6. K11: no first-screen value copy
7. K5: 9-field form

The testimonial sits right after the form, so K8 (trust not near the decision) does
**not** fire. `tests/test_design_qa.py` pins the order and the score.
