# 09: Realign the Claude-facing eval cases with the script-owned skill

**What to build:** The `evals/` Claude cases describe what the script-owned skill (ADR 0005, plugin 1.0.2) must do. Graders that pin the pre-rewrite skill are rewritten to test required information or execution behavior, or deleted. Then one full-suite run on the current bytes records where the skill actually stands.

**Blocked by:** None (can start immediately).

Status: needs-triage

## Why

ADR 0005 states that tests "should verify execution behavior, structured status, and required report information instead of exact prose", and `validation.md` records that the historical fixture tests "remain regression tests for those fixture graders, not evidence that the rewritten skill passed every historical Claude case". No full Claude suite has run since `cc1645e`. Triage on 2026-09-24 deferred these items here:

- Fixed-wording graders superseded by ADR 0005: `alias-astra/scope-line` and `scope-note` (reliability ticket 05); `parallel-two-models/h-consensus`, `h-solo`, `h-divergences`, `merged-llm` and `parallel-one-fails/failed-line` (reliability ticket 13).
- Graders built around the old procedure, not the scripts: temporary-directory, background-run and bare-`cd` checks such as `temp-cleanup`, `two-temp-dirs`, `two-background-runs`, `no-bare-cd`. Each one needs a decision: rewrite it to test the script contract, or delete it.
- Reliability ticket 11 items 4 and 6–9: no grader for an alias-ambiguity or nothing-to-infer question in the final message; grader false positives and blind spots; `gen-ticket11-cases.mjs` still regenerates deleted LLM judges; grader descriptions that name `asks-f12b-*`; the remaining LLM judges (`dispositions`, `merged-llm`).
- Reliability ticket 12: measure `followup-new-blocking` (`c5-not-mentioned`) on the current skill.

## Acceptance criteria

- [ ] Every grader that pins pre-rewrite wording or procedure is rewritten or deleted, with a one-line reason per case in Comments.
- [ ] The offline `evals/_harness/*.test.mjs` files that assert those graders are updated and pass.
- [ ] `gen-ticket11-cases.mjs` cannot regenerate deleted judges.
- [ ] One full-suite run on the current bytes, with the result per case recorded. A case below 1.00 gets a disposition. It is not waived by the main session.

## Notes

The user decided on 2026-09-24 to fix wording defects when real use shows them. This ticket is what makes the eval suite a trustworthy signal again. It is not a request to fix those wording defects.
