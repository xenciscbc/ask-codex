# 15 — The parallel check line is written only about two runs in three

**What to build:** in a parallel consultation, the fixed `Parallel check: …` line is written at the check itself — before `TaskStop`, before asking, before waiting again — on every run, not two in three.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Evidence (resampling at `f5cfb07`, 2026-09-16)

`parallel-shared-timer` with `--runs 3`: **2 of 3 runs passed.** Run 2 failed `check-line-before-stop` ("pattern not found in trace"), meaning no `Parallel check:` line appeared anywhere before the `TaskStop` call; runs 1 and 3 passed.

## Why this matters for the record

Ticket 08 was confirmed on a **single** green run of this case, and its verifier's advisory A1 warned exactly this — that one sample is not evidence of a stable behaviour in a suite known to be nondeterministic. The claim in ticket 08 should be read as "holds in about two runs of three", not "holds".

## Impact

In a parallel consultation the user may be told a run was stopped without ever being told which model was still running at the check — the information the stop decision rests on.

## Acceptance criteria

- [ ] `parallel-shared-timer` passes `check-line-before-stop` on 3 of 3 runs.
- [ ] Ticket 08's comments record the measured reliability rather than the single-run result.
- [ ] The step 8 rule is reworked so the line is tied to an action the model cannot skip, as the fix pass 2 attempted; if a wording change cannot reach 3 of 3, consider having the skill write the line from a command whose output is visible instead.
