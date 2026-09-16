# 16 — A stopped consultation sometimes has no stop report

**What to build:** when a consultation is stopped, the reply always carries the fixed `Consultation stopped: …` line with the interval, the elapsed time, the last event and its age, and the options that were offered.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Evidence (resampling at `f5cfb07`, 2026-09-16)

`timeout-stalled-stop` with `--runs 3`: **2 of 3 runs passed.** Run 1 failed both `stopped-line` ("pattern not found in last_message") and the `stop-report` judge 3-0 — so that run never wrote `Consultation stopped:` at all, not merely a weaker version of it. Runs 2 and 3 were clean.

The same run still behaved correctly otherwise: it attributed nothing to Codex and continued with its own reading of the code, labelled as its own.

## Impact

The user is left without the information the skill promises after a stop — how long it ran, what the last event was, and what the alternatives were — and in the worst case may not realise the consultation was stopped rather than answered.

## Acceptance criteria

- [ ] `timeout-stalled-stop` passes `stopped-line` and `stop-report` on 3 of 3 runs.
- [ ] The fixed line is required at the point of stopping, not only in the final presentation, so a run that ends early still carries it.
