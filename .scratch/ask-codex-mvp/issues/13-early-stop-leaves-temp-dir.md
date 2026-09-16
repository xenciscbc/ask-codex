# 13 — An early stop leaves the temporary directory behind

**What to build:** when a consultation stops before Codex is ever run — a declined project-layer definition, an MCP widening confirmation, a failed MCP guard, or any other early stop after step 1 — the run directory created in step 1 is deleted before the reply, exactly as it is on the normal path.

**Blocked by:** None — can start immediately.

**Status:** resolved — fixed and verified 2026-09-16 (see Comments; reliable, not proven deterministic)

## Evidence (final suite at `f5cfb07`, 2026-09-16)

Five cases failed `temp-cleanup` ("Bash called 0x, expected 1..∞") — four of them failing that grader alone, while `project-layer-aborts-01` also failed the `user-told-which-definition` judge (FAIL/FAIL/PASS), which the fixed bytes later cleared:

- `diagnosis-leak-control` (0.92) — a normal consultation that *did* run `codex exec`, so a run directory certainly existed.
- `project-config-table` (0.83), `project-layer-aborts-01` (0.67), `project-layer-decline-aborts` (0.83), `project-widening-confirm` (0.83) — all abort before any `codex exec`.

This is not a grader bug. The skill creates the run directory in **step 1** (`mktemp -d`), while the aborts happen in step 3 (project-layer definitions) and steps 4–5 (listings, guard, widening confirmation), and step 11 already says to clean up "on every early stop after step 1". So the directory existed and was not removed.

## Impact

`prompt.md` (which contains excerpts of the user's code), `events.jsonl` and `last-message.json` stay on disk under the temp base after a consultation the user was told had stopped.

## Acceptance criteria

- [ ] Each abort path in steps 2–7 names the cleanup explicitly, so stopping cannot skip it.
- [ ] The five cases above pass `temp-cleanup` on a rerun.
- [ ] A regression sample of healthy cases (normal consultation, parallel, follow-up, failure path) still passes, since step 11 is on every path.
- [x] The skill states the rule once, in one place, rather than repeating a cleanup block per branch.

## Comments

**2026-09-16 — fixed in six edits, verified on nine cases.** The rule already existed ("on every early stop after step 1") and the Failures table already said "Clean up (step 11)"; what was missing was the rule biting at each stop and on the normal path. Changes: step 3's decline, step 4's failed listing, step 4's invalid server name and step 5's guard mismatch each now say **clean up (step 11)** explicitly; step 11 opens with "**Every stop is a cleanup.**" and enumerates the stops; and step 10 gained a precondition — "**Before you write this answer, the run directories must already be gone**" — aimed squarely at `diagnosis-leak-control`, which had leaked on the *normal* path after a successful `codex exec`.

**Verification (reruns at the fixed bytes).** All five originally leaking cases now pass `temp-cleanup`: `project-config-table` 1.00, `project-layer-aborts-01` 1.00, `project-widening-confirm` 1.00, `diagnosis-leak-control` (cleanup passes; see the note below), and `project-layer-decline-aborts` — which **failed once and passed 1.00 on a rerun**, so the behaviour is reliable but not proven deterministic; treat "always cleans up" as roughly-always until a `--runs 3` sample says otherwise. Regression sample unaffected: `manual-with-question`, `followup-carries-claims`, `fail-nonzero-exit` and `mcp-guard-blocks` all 1.00, which matters because steps 10 and 11 sit on every path. Offline: `claude plugin validate` passes and all ten harness suites stay green.

**Correction to the original evidence.** This ticket listed five "leaking" cases from the final suite, but `diagnosis-leak-control` is a **red-phase control**: slice-02 marks it "(red phase only)" and requires its `no-hypothesis` grader to fail inside the harness. In the final suite that grader passed and only `temp-cleanup` failed; in the rerun the reverse happened. So its cleanup leak was real and is fixed, while its remaining sub-1.00 score is the control doing its job — not a defect, and it should not be counted as a suite failure in the final report.
