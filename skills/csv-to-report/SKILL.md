---
name: csv-to-report
description: Convert a raw CSV into a structured, business-ready report using a 3-step framework — load + label, define rules, request structured deliverables. Trigger when the user says "csv to report", "report from this csv", "summarize this spreadsheet", "training log report", "compliance report", "turn this data into a report", or uploads a CSV and wants narrative output rather than raw numbers.
---

# csv-to-report

**Family:** content-and-data
**Status:** Stable

## Purpose

Turn raw CSV data into a structured, narrative report. A small Python helper does
the deterministic profiling/filtering/grouping; the skill adds the human layer —
what the columns mean and what the business rules are.

The 3-step framework: **Load + label** → **Define rules** → **Request the
structured deliverable**, then iterate (same data, new lenses). Common uses:
training compliance, staff scheduling, billing audits, inventory snapshots.

## Triggers

- "csv to report" / "report from this csv"
- "summarize this spreadsheet"
- "training log report" / "compliance report"
- "turn this data into a report"

## Inputs

- CSV file (path or pasted)
- Column meanings (labels the agent needs to interpret correctly)
- Business rules (what counts as overdue, complete, required, etc.)
- Desired deliverable format

## Steps

1. **Profile the data mechanically:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow/csv_to_report.py" --in <file.csv> --human
   ```
   Returns row/column counts, per-column type + fill rate + distinct values,
   numeric stats, and top categories — so labeling is grounded in real data.
2. **Load + label.** Confirm what each non-obvious column means (abbreviations,
   joined fields, date formats). Flag data-quality issues the profile reveals
   (blanks, mixed types, totals rows mixed into data rows).
3. **Define rules.** Capture explicit business rules ("annual training expires 365
   days after Completion_Date"; "overdue = past expiration AND status != complete").
4. **Slice as needed** using the helper's `--filter`, `--group-by`, and `--select`
   flags to answer specific questions deterministically.
5. **Render the deliverable** — table, grouped lists, narrative summary, or an
   exported sub-CSV — applying the business rules to the profiled data.
6. **Offer an iteration menu** — filter, group, export, re-summarize on the same
   data ("now only clinical staff", "now group by training type").

## Outputs

- Structured report (Markdown or HTML)
- Optional filtered sub-CSV(s) for downstream use

## Dependencies

- `scripts/workflow/csv_to_report.py` (required) — Python 3.10+, standard library only (no pandas)

## Notes

Output quality scales with input quality: the helper surfaces clean-CSV issues
(inconsistent dates, merged cells, totals rows) so they're flagged before the
report is generated. Data stays local — see `PRIVACY.md`.
