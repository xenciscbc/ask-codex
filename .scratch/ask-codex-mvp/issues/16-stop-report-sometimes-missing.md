# 16 — A stopped consultation sometimes has no stop report

**What to build:** when a consultation is stopped, the reply always carries the fixed `Consultation stopped: …` line with the interval, the elapsed time, the last event and its age, and the options that were offered.

**Blocked by:** None — can start immediately.

**Status:** resolved — by reliability slice 03, at a measured rate (2026-09-18)

## Evidence (resampling at `f5cfb07`, 2026-09-16)

`timeout-stalled-stop` with `--runs 3`: **2 of 3 runs passed.** Run 1 failed both `stopped-line` ("pattern not found in last_message") and the `stop-report` judge 3-0 — so that run never wrote `Consultation stopped:` at all, not merely a weaker version of it. Runs 2 and 3 were clean.

The same run still behaved correctly otherwise: it attributed nothing to Codex and continued with its own reading of the code, labelled as its own.

## Impact

The user is left without the information the skill promises after a stop — how long it ran, what the last event was, and what the alternatives were — and in the worst case may not realise the consultation was stopped rather than answered.

## Acceptance criteria

- [x] `timeout-stalled-stop` passes `stopped-line` and `stop-report` on 3 of 3 runs.
- [x] The fixed line is required at the point of stopping, not only in the final presentation, so a run that ends early still carries it.

## Comments

**2026-09-18 — resolved by reliability slice 03, with the rate recorded.** The report is no longer composed by the model: `stop.sh` prints the complete `Consultation stopped:` line (interval and source, elapsed, last event and age or "no events", the offered options and recommendation, `process tree ended` / `NOT confirmed — pids …`, and in a parallel run `done — …; still running — …`), and the model copies it twice — at the stop and as the first line of the final answer, the latter shown again by the stopped run's cleanup line (`cat -- '<tmp>/stop-report'; rm -rf -- '<tmp>'`). Measured on the final bytes over three rounds of `timeout-stalled-stop --runs 5`: line present with every field in the final answer **14/15** (the miss: the answer opened with the line, then a `Read` split it into a second message), line written before `TaskStop` **12/15** (the misses: `TaskStop` called in a message with no text). Probe D had shown the old shape — never at the stop, improvised at the end, incomplete 2 of 3 — so both halves improved; the residual is model-level and accepted by the user. Result directories and traces: ticket 03's Comments.
