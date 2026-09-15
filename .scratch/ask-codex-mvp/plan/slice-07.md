# Slice 07 — Timeout monitoring (revision 3, closing review)

## Readiness record

- Round 1 REVISE (3 blockers) → revision 2.
- Round 2 REVISE (2 blockers) — the second automatic REVISE. Every blocker is dispositioned below; revision 3 opens a new readiness epoch with exactly one closing fresh review; another REVISE pauses the slice for the user.

| Round-2 blocker | Disposition | Where |
|---|---|---|
| B1 case 2's grader expects fields the final stop message is not required to contain | FIX — the stop report (a Failures-path final message) must contain: the interval in force, elapsed time, the last event and its age, the two options that were offered with the recommendation, and that the consultation was stopped; case 2's grader checks exactly these | Outcome "Stop"; case 2 |
| B2 the probe cannot decide the no-`TaskOutput` route (completion-notification wake-up untested) | FIX — a second probe `bg-notify-probe` runs only if `TaskOutput` is unusable; the route table covers every outcome combination | Probe section |

- Closing review REVISE (1 blocker: the probe's tool grant differed from the cases' grant, so a probe pass would not prove the tools exist in case runs) → FIX in place: probe and every ticket-07 case run use `--allow-tools Bash Write TaskOutput TaskStop`; acceptance 2 made route-conditional; case-table layout fixed. Slice paused for the user's decision (cap reached).

Revision 2 fixes round 1 (REVISE, 3 blockers): (1) a tool probe before any red run decides whether `TaskOutput`/`TaskStop` are usable in eval children, with a defined route for each outcome; (2) case 2 proves the stop with a `TaskStop` tool-use grader (or, if unavailable, a recorded narrowing); (3) timer notices are restated in the final answer's first item, so last-message graders can see them.

Ticket: `.scratch/ask-codex-mvp/issues/07-timeout-monitoring.md` (spec stories 69–73 on waiting and liveness; the ticket cites 59–63, 67). Envelope, F-map (F8, F11), stops, budget: `PLAN.md`. Blocked by 01 (resolved). Serial order: after 04. **Entry gate:** ticket 04's outcome verifier CONFIRMED (or its required fixes committed) and recorded in ticket 04 Comments. Budget ≤ $6 eval, 0 live Codex calls (program cap $75; projection is tight — keep lean).

## Outcome

While a consultation runs in the background, Claude checks it every **interval T** (default 30 minutes; `EVAL_ASK_CODEX_TIMEOUT_MINUTES` overrides it) and judges **liveness** only from (a) the tracked background task's state and (b) the age of the last event in `<tmp>/events.jsonl` — never from CPU or process listings. **Staleness threshold S = T/6** (5 minutes by default).

- **Confirmed alive** (task still running and the last event is at most S old): one-line notice — elapsed time, the last event's type and age — then wait another T. No question.
- **Not confirmed** (task running but the last event is older than S): ask with `AskUserQuestion`, showing elapsed time and the last event with its age, options "wait another T minutes" / "stop this consultation". Recommendation: "wait" when the last event is at most T/2 old (the run still shows recent activity); "stop" otherwise (stalled). Waiting re-arms the timer; there is no cap on how often the user may wait.
- **No `AskUserQuestion`** (non-interactive session): Claude cannot wait for an answer without ending its turn, which would orphan the run. It states the same question and recommendation in text and takes **stop** (consistent with the existing "no `AskUserQuestion` → ask in text and stop" rule for confirmations), saying so.
- **Stop**: end the background task (`TaskStop` on the tracked task), then handle it as a failure per ticket 04 (nothing attributed to Codex; step 11 cleanup; carry on). The **final stop report** — the last message, after cleanup — must state: the interval in force (default or override), the elapsed time, the last event and its age (or "no events"), the two options that were offered ("wait another T minutes" / "stop this consultation") with the recommended one, and that the consultation was stopped. F8 (the whole Codex process chain ends) is confirmed in ticket 09 live acceptance.
- **Override (F11)**: read with `printenv EVAL_ASK_CODEX_TIMEOUT_MINUTES`; valid only as a positive integer (`^[1-9][0-9]*$`) → one-line notice that the override is active (T and S shown); anything else (empty is simply "unset") — zero, negative, non-numeric, decimal — is ignored with a notice and the default 30 minutes applies.
- **Timer mechanism.** Preferred: `TaskOutput` on the tracked task with `block: true` and a timeout of min(remaining T, 10 minutes), repeated until T has elapsed (an early completion ends the wait at once). Alternative when `TaskOutput` is unavailable: a background Bash timer task (`sleep <T seconds>`, `run_in_background: true`) whose completion notification marks the end of the interval; the consultation's own completion notification ends the wait early. Which one the skill uses in evals is decided by the probe below.
- **Final answer restates the timer.** Step 10 item 1 also states the timer outcome in one line: the interval in force (default, override active, or override ignored and why) and how many liveness checks ran with their result (e.g. "1 check: still running, last event 4 s ago"). The in-run notices are still shown when they happen.

## First task — tool probe (before any red run)

Probe case `task-tools-probe` (no skill, haiku, `allowed_tools: [Bash, TaskOutput, TaskStop]`, run with **the same grant as the cases**: `--allow-tools Bash Write TaskOutput TaskStop`, ~$0.05): prompt "Start `sleep 120` with Bash `run_in_background: true`. Call `TaskOutput` on that task with `block: true` and `timeout: 5000` and report the status it returns. Then call `TaskStop` on it and report the result." Graders: `tool_used TaskOutput min 1`, `tool_used TaskStop min 1`, and a last-message llm grader that the task was reported running and then stopped. (If `--allow-tools` rejects these names, rerun without them in the grant and record which form worked.)
Second probe `bg-notify-probe` — run **only if `TaskOutput` is unusable** (no skill, haiku, `allowed_tools: [Bash]`, ~$0.05): prompt "Start `sleep 20` with Bash `run_in_background: true`. Do not call any tool while it runs. When its completion notification arrives, reply with the single word NOTIFIED." Graders: last message matches `NOTIFIED`; `tool_used Bash max 1`. Pass → a background-Bash completion notification wakes the headless child without ending the turn.

Route table (timer, stop) — every outcome maps to one route:

| `TaskOutput` | `bg-notify-probe` | `TaskStop` | Timer used | Stop path | Cases |
|---|---|---|---|---|---|
| usable | not run | usable | `TaskOutput` waits | `TaskStop` | 1–5 as specified (case 2 keeps `tool_used TaskStop min 1`) |
| usable | not run | unusable | `TaskOutput` waits | report + cleanup only | 1, 3–5 as specified; case 2 without its `TaskStop` grader; "stop terminates the run" + F8 → ticket 09 (stop 5) |
| unusable | pass | usable | background-Bash `sleep T` timer | `TaskStop` | 1–5 as specified |
| unusable | pass | unusable | background-Bash timer | report + cleanup only | as row 2 |
| unusable | fail | any | none available | — | stop (5): cases 1–2 → ticket 09; cases 3–5 stay |

The probe results (tool names, usable or not, notification outcome, cost) and the chosen route are recorded in ticket 07 Comments before any red run.

## Scope

- `skills/ask/SKILL.md` step 8: the timer, liveness check, notices, question, non-interactive fallback, stop path; step 11 unchanged.
- Stub: `exec.mode: "slow-active"` (emits a progress event every `event_every_s` seconds for `duration_s`, then the valid reply) and `"slow-silent"` (emits `thread.started` and then nothing for `duration_s` seconds, then exits 1; killable at any time; writes `.stub/exec-finished` only when it ends by itself). Offline stub test extended (short durations).
- Cases (below), ticket 07 comments. Not in scope: parallel runs' shared timer (ticket 08).

## Eval cases (runs 1, sonnet, `--allow-tools Bash Write TaskOutput TaskStop` for every ticket-07 red and green run — the grant form the probe verified; cases 1–2 also list `TaskOutput` and `TaskStop` in `allowed_tools` per the route; the first red transcript must show no "not granted" notice for them; `execution.env: {EVAL_ASK_CODEX_TIMEOUT_MINUTES: …}` — `EVAL_*` reaches the agent's shell, confirmed in ticket 04)

| # | Case | Override | Stub | Expected | Graders beyond the standard set |
|---|---|---|---|---|---|
| 1 | `timeout-alive-notice` | `1` (T 60 s, S 10 s) | slow-active: event every 5 s for 100 s | one liveness check confirms → notice, keep waiting, result presented | last-message llm: item 1 states the override is active (1 minute) and at least one liveness check found the run still running with a recent last event; claims presented with dispositions (a presented result also proves no question stopped the run — in evals a question would end in stop) |
| 2 | `timeout-stalled-stop` | `1` | slow-silent 600 s | check finds no event within S → text question with both options, stop recommended → stop | `tool_used TaskStop min 1` (per the route table); last-message llm on the **final stop report**: states the interval in force (1 minute override), the elapsed time, the last event and its age (or no events), both options with "stop" recommended, that the consultation was stopped, and attributes nothing to Codex; `temp-cleanup` |
| 3 | `timeout-override-invalid-text` (F11) | `abc` | valid (fast) | override ignored with a notice, default used, normal result | last-message llm: item 1 says the override `abc` was ignored and the default 30 minutes applies |
| 4 | `timeout-override-invalid-zero` (F11) | `0` | valid (fast) | same | same, for `0` |
| 5 | `manual-with-question` (01 regression) | none | valid | as in 01 | as in 01 |

**Deterministic graders (added after ticket 04's verifier showed that llm graders alone can pass a reply missing a required element — a tightening, not a scope change).** The skill starts each notice with fixed wording (`Timeout override active:`, `Timeout override ignored:`, `Codex still running —`, `Consultation stopped:`), and each case adds last-message regex graders for its lines: case 1 `Timeout override active:` and `Codex still running`; case 2 `Consultation stopped:`; cases 3–4 `Timeout override ignored:` plus the value (`abc` / `"0"`). An offline test applies these patterns to hand-written correct and incomplete replies before any paid run. The llm graders stay for the remaining fields.

All notice graders are last-message llm graders: cases 1, 3, 4 read step 10 item 1 (the restated timer line); case 2 reads the final stop report, whose required fields are listed under Outcome "Stop". None relies on text shown only mid-run.

Standard set: `skill-fired`, one `codex exec`, exec sentinel, `no-violations`, `no-bare-cd`, `temp-cleanup`. A negative override is covered by the same rule (`^[1-9][0-9]*$`) and by skill-text review; not a separate paid case.

## Red plan

Cases 1, 2, 3 on the ticket-04 skill: expected failures — 1 (no override/liveness notice), 2 (the run is waited to its end or orphaned; no question), 3 (no notice about the invalid override).

## Acceptance

1. `claude plugin validate`; offline stub test (slow modes) and the existing offline checks pass.
2. Cases pass per the chosen route (route table): all of 1–5 on route 1 or 3; case 2 without its `TaskStop` grader on routes 2/4; cases 3–5 only on route 5 (cases 1–2 moved to ticket 09).
3. SKILL.md step 8 contains the timer, liveness rule (task state + last-event age only), notices, question and recommendation rule, non-interactive fallback, stop path, override validation.
4. Fresh verifier CONFIRMED on F11 and the ticket-07 criteria, except F8 process-chain termination and the interactive `AskUserQuestion` branch (both ticket 09 live acceptance, recorded).

## Budget and stops

Eval cap $6: tool probe ~$0.05 (+ notification probe ~$0.05 only if needed); red 3 cases ~$1.3; green 5 cases ~$2.3 (slow cases take minutes of wall time, similar token cost); iterations ≤ $1.5. No live Codex calls. Global stops apply.

## Open design points for review

- The "wait" recommendation threshold (last event ≤ T/2) is this slice's interpretation of "recommended when the run looks active".
- The non-interactive fallback (take stop) is inferred from the existing confirmation rule; ticket 09 live covers the interactive branch.
