---
template: qa-report-template
used_by: [qa-gate]
purpose: Structured 9-phase pre-delivery QA output with an explicit client-ready verdict.
---

QA SUMMARY REPORT
═════════════════
Project:    {{project}}
URL / path: {{target}}
Date:       {{date}}
Auditor:    designer-pro-and-seo:qa-gate

OVERALL STATUS: {{status}}        <!-- PASS | CONDITIONAL PASS | FAIL -->
RISK RATING:    {{risk}}          <!-- Low | Medium | High | Critical -->
CLIENT-READY:   {{client_ready}}  <!-- YES | NO -->
ESTIMATED FIX TIME: {{fix_hours}} h

── Phase results ───────────────────────────────
1. Functional integrity .......... {{p1}}
2. Visual fidelity ............... {{p2}}
3. Accessibility (WCAG) .......... {{p3}}
4. Performance (CWV) ............. {{p4}}
5. Security ...................... {{p5}}
6. Content completeness .......... {{p6}}
7. SEO baseline ................. {{p7}}
8. Cross-device / browser ........ {{p8}}
9. Deployment readiness .......... {{p9}}
   (each: PASS | WARN | FAIL | N/A)

🔴 CRITICAL ISSUES (must fix before delivery)
{{critical}}

🟡 WARNINGS (should fix)
{{warnings}}

🟢 RECOMMENDATIONS
{{recommendations}}

⚪ NICE-TO-HAVES
{{nice_to_haves}}

── Verdict ─────────────────────────────────────
{{verdict_note}}

Rule: any unresolved CRITICAL ⇒ OVERALL = FAIL and CLIENT-READY = NO.
CONDITIONAL PASS is allowed only when remaining items are WARN-level or lower.
