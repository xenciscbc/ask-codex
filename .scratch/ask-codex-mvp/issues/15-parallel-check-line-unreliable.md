# 15 — The parallel check line is written only about two runs in three

**What to build:** in a parallel consultation, the fixed `Parallel check: …` line is written at the check itself — before `TaskStop`, before asking, before waiting again — on every run, not two in three.

**Blocked by:** None — can start immediately.

**Status:** resolved — by reliability slice 03 (2026-09-18)

## Evidence (resampling at `f5cfb07`, 2026-09-16)

`parallel-shared-timer` with `--runs 3`: **2 of 3 runs passed.** Run 2 failed `check-line-before-stop` ("pattern not found in trace"), meaning no `Parallel check:` line appeared anywhere before the `TaskStop` call; runs 1 and 3 passed.

## Why this matters for the record

Ticket 08 was confirmed on a **single** green run of this case, and its verifier's advisory A1 warned exactly this — that one sample is not evidence of a stable behaviour in a suite known to be nondeterministic. The claim in ticket 08 should be read as "holds in about two runs of three", not "holds".

## Impact

In a parallel consultation the user may be told a run was stopped without ever being told which model was still running at the check — the information the stop decision rests on.

## Acceptance criteria

- [x] ~~`parallel-shared-timer` passes `check-line-before-stop` on 3 of 3 runs.~~ 改寫（reliability slice-03 rev 3）：`check-line-before-stop` 隨「行動前先寫 `Parallel check:`」規則一起刪除；取代證據為 `parallel-info-before-stop`（done/still-running 欄位出現在 `TaskStop` 之前的 assistant 訊息）與 `stopped-report`（最終訊息含完整停止報告行與並行欄位）在 `--runs 5` 全數通過。
- [x] Ticket 08's comments record the measured reliability rather than the single-run result.
- [x] The step 8 rule is reworked so the line is tied to an action the model cannot skip, as the fix pass 2 attempted; if a wording change cannot reach 3 of 3, consider having the skill write the line from a command whose output is visible instead.

## Comments

**2026-09-18 — resolved by reliability slice 03.** The pre-action rule ("write `Parallel check:` before you act") was the unreliable part and is gone; the parallel state now rides on text the model necessarily writes: the parallel form of the still-running notice, the first line of the question text, and the `Consultation stopped:` line printed by `stop.sh` with `--done`/`--still-running`. Measured on the final bytes: `parallel-info-before-stop` (the fields on an assistant line before `TaskStop`) **15/15**, `check-line` (one `Parallel check:` line per check in the final answer) **15/15**, `stopped-report` 15/15 — three rounds of `parallel-shared-timer --runs 5`. Ticket 03's Comments list the result directories and traces.

**2026-09-20 — live evidence.** The stop line was copied from `stop.sh` at the moment of the stop and again as the first line of the final answer in both live runs on real Codex (headless and interactive): `.scratch/ask-codex-reliability/evidence/04-live-stop.md`, replies in `04-live-H-reply.md` and `04-live-I-reply.md`.
