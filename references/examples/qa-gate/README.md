# Golden example — qa-gate (static path: `qa_gate.py`)

`build/` is a two-page static site (fictional brand) that looks finished but isn't:
- the staging `robots.txt` (`Disallow: /`) shipped
- an AWS-style access key sits in an inline script
- the home page still has lorem ipsum
- the hero image file is missing
- a `href="#"` placeholder link remains
- the email form has no action

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/qa_gate.py" --dir references/examples/qa-gate/build \
  --base-url https://example.test --project "Cedar Bench Co." --report --as-of 2026-09-25
```

## Expected result

`OVERALL STATUS: FAIL`, `RISK RATING: Critical` (a security critical), `CLIENT-READY: NO`.

**Phases:**

| Phase | Status | Why |
|---|---|---|
| 5 Security | FAIL | exposed secret |
| 6 Content | FAIL | lorem ipsum placeholder |
| 9 Deployment | FAIL | robots.txt blocks Googlebot |
| 7 SEO | WARN | no JSON-LD |
| 2, 8 | N/A | need Playwright |

**Critical issues:**
- the exposed AWS access key, with a fix to rotate the credential
- the leaked lorem-ipsum placeholder, reported once even though two engines see it
- robots.txt blocking Googlebot

**Warnings:** the missing hero image and no JSON-LD on either page.

**Recommendations:** the `#` link, the action-less form, image format and srcset, and
missing Open Graph. Plus deployment items: no sitemap, no 404 page, no analytics tag.

`tests/test_design_qa.py` pins the verdict, the risk and the critical set. For
contrast, the 9-page `seo-sitemap/site` example comes back **CONDITIONAL PASS**: no
criticals, one broken link and missing meta as warnings.
