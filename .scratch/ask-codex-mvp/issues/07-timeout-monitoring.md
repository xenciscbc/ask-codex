# 07 — Timeout monitoring

**What to build:** A long-running consultation is checked every 30 minutes. If liveness is confirmed — the background task is alive and the event stream received a new event within the staleness threshold (5 minutes) — Claude re-arms the timer and tells the user in one line (including the last step). Otherwise Claude asks via `AskUserQuestion`, showing elapsed time and the last event with its age, with the options "wait another 30 minutes" (recommended when the run looks active) and "stop this consultation" (recommended when it looks stalled). Stopping ends the Codex run and is handled like any other failure (ticket 04 behaviour). `EVAL_ASK_CODEX_TIMEOUT_MINUTES` overrides the check interval; the staleness threshold stays at one sixth of the interval. See spec: user stories 59–63, 67.

**Blocked by:** 01 — Manual consultation tracer bullet.

**Status:** ready-for-agent

- [ ] Liveness is judged only from the tracked background task state and the event stream's last-event age — never from CPU or process listings.
- [ ] Confirmed-alive checks re-arm silently apart from a one-line notice; no `AskUserQuestion`.
- [ ] Unconfirmed checks ask with the two options and the correct recommendation; there is no cap on how many times the user can choose to wait.
- [ ] "Stop" terminates the run, cleans up temporary files, reports briefly, and Claude continues its work.
- [ ] The interval override works and the staleness threshold scales with it.
- [ ] Eval cases pass with a small override: stub emitting periodic events → no prompt and a one-line notice; stub emitting no events → prompt offered with "stop" recommended.
- [ ] Eval `timeout-override-invalid` (F11): a zero, negative or non-numeric override is ignored (default interval used) with a notice; a valid override shows a notice that it is active.
- [ ] Stop terminates the whole Codex process chain; the live check in ticket 09 confirms no Codex process remains (F8).

## Comments

**2026-09-15 — slice-07 readiness.** Three plan-verifier rounds (REVISE ×2, then a closing REVISE with one blocker) led to: a tool probe (`TaskOutput`/`TaskStop`, run with the same grant as the cases) and a conditional notification probe, with a route table mapping every outcome to one timer/stop mechanism (routes that lose a tool move the affected criterion to ticket 09 under stop (5)); the timer outcome restated in the final answer's first item and a required field list for the final stop report, so last-message graders see them; a `tool_used TaskStop` grader proving the stop; every ticket-07 run granted `--allow-tools Bash Write TaskOutput TaskStop`. Design interpretations: liveness from the tracked task's state plus the age of the last event in `events.jsonl` only; "wait" is recommended when the last event is at most T/2 old, otherwise "stop"; without `AskUserQuestion` the question is stated in text and "stop" is taken (the run would otherwise be orphaned when the turn ends); the override must be a positive integer. The user approved execution after the closing review's blocker was fixed in the contract; work starts once ticket 04 is confirmed.
