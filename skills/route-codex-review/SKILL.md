---
name: route-codex-review
description: Forced adversarial review pre-delivery — hands Claude-generated code, content, or plans to Codex (GPT-5.5) to find bugs, security risks, missing tests, and missed edge cases. Trigger when the user says "review the code you wrote", "check your work", "second opinion", "sanity check this", "adversarial review", or before client-bound delivery of substantial Claude output.
---

# route-codex-review

**Family:** routing
**Status:** Stable

## Purpose

The execution arm of the no-self-review rule. Hands Claude's output to Codex for an
independent, adversarial pass — bugs, security risks, missing edge cases/tests,
broken invariants, unclear logic. Mandatory for substantial output heading to a
client or production, or whenever the user asks to verify Claude's work.

## Triggers

- "review the code you wrote" / "review what you just did"
- "check your work" / "look over what you wrote" / "give it a once-over"
- "second opinion" / "sanity check this code" / "double-check this"
- "adversarial review" / "have codex review" / "is this right"

> Scoped to **Claude's own output**. Bare "audit this" / "audit my site" belongs
> to the SEO/QA families, not here (see `references/ENGINE-CONTRACTS.md` §3).

## Inputs

- The output to review (diff, files, content, or plan)
- Review focus (bugs / security / correctness / completeness / all)

## Steps

1. **Check Codex is available:** `codex --version`. If absent, tell the user it's
   off until installed and offer a structured manual review *from a different lens*
   (never a same-model self-review).
2. **Bundle the context** — the diff or the specific files, plus what was tried and
   the relevant constraints.
3. **Invoke Codex:**
   ```
   git diff | codex exec --skip-git-repo-check "Review this diff. Find bugs, security risks, missing tests, edge cases. Be specific and adversarial."
   ```
   For untracked code, pipe the file(s) instead of `git diff`. For a harder pass:
   `...codex exec ... "Adversarial review. Challenge the design. Prove what's broken."`
4. **Parse** Codex's findings into severity-tagged items (Critical → nits).
5. **Integrate, don't rubber-stamp.** For each finding decide fix / defer / dismiss
   (with a reason). Apply the fixes, then re-verify.

## Outputs

- A severity-tagged findings list from Codex
- The integrated outcome: what was fixed, deferred, or dismissed (with reasons)

## Dependencies

- The `codex` CLI installed (or the adjacent `openai-codex` tool). Degrades to a
  documented, different-lens manual review when absent.

## Notes

Claude reviewing its own substantive output repeats its own blind spots; this skill
operationalizes routing that review to a different model before it ships.
