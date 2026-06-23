---
name: route-three-brain
description: The routing law for handing off between Claude (primary driver), Codex/GPT-5.5 (adversarial review, second opinions), and Gemini (long-context, repo-wide synthesis). Codifies when each model is the right tool and enforces the no-self-review rule. Trigger when the user says "three brain", "route this", "which model should", "delegate to codex / gemini", or when a substantial Claude output needs an independent check.
---

# route-three-brain

**Family:** routing
**Status:** Stable

## Purpose

The decision layer for cross-model routing. Three models, three roles:

- **Claude** — primary driver for code, content, design generation, conversation.
- **Codex / GPT-5.5** — adversarial review, second-opinion debugging, deep
  correctness/security checking.
- **Gemini** — large-context whole-repo analysis, multi-document synthesis, big
  structured-data passes.

**Hard rule:** Claude never reviews Claude — same architecture, same blind spots.
If the user says "check your work" / "review this" / "is this right" / "second
opinion" / "sanity check," route to Codex via `route-codex-review`.

## Triggers

- "three brain" / "tri-brain" / "route this" / "which model"
- "delegate to codex" / "delegate to gemini" / "best model for X"

## Inputs

- Task description; the current output (if asking for review/handoff)
- Constraints (cost, time, privacy)

## Steps

1. **Startup self-check (once per session).** Verify the tools exist:
   `codex --version` and `gemini --version`. If one is missing, announce it once and
   route only to what's available.
2. **Classify the task:**
   - Build/generate/converse → **Claude** keeps it.
   - Review / verify / debug a substantial output, or any risk-path edit (auth,
     billing, migrations, deploy, secrets) → **Codex** via `route-codex-review`.
   - Needs more context than one window (whole repo, many docs) → **Gemini** via
     `route-gemini-context`.
3. **Announce forced routes** in one line before running (so the user can interrupt):
   `[three-brain] routing to Codex (review) — risk path: src/auth/`.
4. **Execute** the handoff via the execution skills and **integrate** the result —
   diff where models agree/disagree and adjudicate by evidence, not by averaging.

## Outputs

- A routing decision with justification
- The integrated result of any executed handoff

## Dependencies

- `route-codex-review` (Codex execution), `route-gemini-context` (Gemini execution)
- The `codex` and `gemini` CLIs installed (or the adjacent `openai-codex` /
  `cc-gemini-plugin` tools); degrades to a recommendation when neither is present

## Notes

The law layer; the two `route-*` skills are the execution layers. Under-firing is
fine; over-firing breaks trust. When uncertain, recommend rather than auto-route.
