# Slice 03 — Stop path through the shipped scripts (revision 1)

Ticket: `.scratch/ask-codex-reliability/issues/03-stop-path-in-skill-and-evals.md`. Spec: `.scratch/ask-codex-reliability/spec.md` (stories 4–7, 11, 19; the fixed report line under 「停止報告固定欄位」; the stop order under 「停止順序」). Blocked by 01 and 02 — both satisfied for this slice: 02 is resolved (`c198a37`); 01's probes A–D are in `evidence/01-stop-behaviour.md` (probe E concerns ticket 06 only). Mode AUTO (approved with the programme). No Claude eval budget cap; **0 live Codex calls** (live proof is ticket 04).

## Evidence this slice rests on

- **Probes A/B:** after `TaskStop` the whole `sh → node → codex.exe` chain keeps running to completion in *both* the interactive and the headless session, so the fix is unconditional. Ticket 12's "headless only" scope statement is wrong and is corrected by this slice's Comments.
- **Probe D (three kept traces):** the `Consultation stopped:` line was never written at the moment of the stop; it was improvised once in the final message, and 2 of 3 improvisations were judged incomplete (options missing; elapsed muddled). The remedy is therefore twofold: the line comes from the script (fields cannot be improvised) and is written twice (at the stop, restated in step 10).
- **Ticket 15's failing run:** the check happened inside a message with no text at all. Fixed wording that must precede an action is unreliable, so the parallel information moves into text the model necessarily writes.

## Outcome

1. **Launch through `run.sh`.** Step 8's command becomes `bash '<skill directory>/scripts/run.sh' '<tmp>' -- codex exec … - < '<tmp>/prompt.md' > '<tmp>/events.jsonl' 2> '<tmp>/stderr.log'`, still one line, still `run_in_background: true`; the `codex exec` part and its redirections are unchanged. The `pid` file lands in the run directory; step 11 removes it with the directory.
2. **Stop through `stop.sh`, then `TaskStop`.** The stop path is: (a) run `bash '<skill directory>/scripts/stop.sh' '<tmp>' --interval <T> --interval-source <default|override> --recommended <wait|stop>` (plus `--done '<full slugs or none>' --still-running '<full slugs>'` in a parallel consultation, once per run being stopped); (b) write the `Consultation stopped:` line the script printed, **verbatim, as the first line of the message in which you call `TaskStop`**; (c) call `TaskStop` on that run's task whether or not the task already ended; (d) clean up (step 11); (e) restate the same line word for word in step 10 item 1. When the script exits non-zero its line ends `process tree NOT confirmed — pids <…>`: copy it unchanged, and tell the user the stop could not be confirmed and which pids are listed; never rewrite it to "ended".
3. **Parallel information travels with text the model must write.** The pre-action rule ("never stop, ask or wait without having written `Parallel check:` first") is deleted. Instead, in a parallel consultation: the confirmed-alive notice ends with `; done — <full slugs or none>; still running — <full slugs>`; the `AskUserQuestion` question body's first line is `Parallel check: done — …; still running — …`; the stop report carries `; done — …; still running — …` (printed by the script from the arguments); step 10 still lists one `Parallel check: done — …; still running — …` line per check that ran. Liveness judgement is unchanged (task state and last event only).
4. **Ticket 12/15/16 close offline**; ticket 12's scope is corrected to "both session kinds" with the live proof deferred to ticket 04.

## Non-goals

No change to the check interval, staleness threshold, `TaskOutput`/timer waiting, the Failures table, cleanup wording, the merged parallel presentation, or the READMEs/ADR (ticket 04). No general Codex process management. No new stub mode.

## Scope (files)

- `skills/ask/SKILL.md` step 8 (command; stop path; fixed wording: the stop report is now "the line `stop.sh` printed"; parallel paragraph rewritten per outcome 3), step 10 item 1 (restate the stop line; parallel check lines per check), step 11 (unchanged text — verify the `pid` file is inside `<tmp>`).
- `evals/timeout-stalled-stop/graders/`: `used-stop-script.md` (new, `tool_used` Bash, `input_match` `stop\.sh`), `stopped-line.md` (rewritten: full-field regex on the last message, must contain `process tree ended`), `stopped-at-stop.md` (new, `target: trace`, `Consultation stopped:[\s\S]*"name":"TaskStop"` — the line precedes the `TaskStop` call), `stop-report.md` (LLM, reworded to the fixed fields), keep `used-taskstop`, `one-codex-exec`, `temp-cleanup`, `no-bare-cd`, `skill-fired`.
- `evals/parallel-shared-timer/graders/`: delete `check-line-before-stop.md`; add `parallel-info-before-stop.md` (`target: trace`: `done [—-] [*\x60]*gpt-5\.6-sol[*\x60]*; still running [—-] [*\x60]*gpt-6-astra[\s\S]*"name":"TaskStop"`), `used-stop-script.md`, `stopped-report.md` (last message: the full-field `Consultation stopped:` line with `process tree ended` and `; done — gpt-5.6-sol; still running — gpt-6-astra`); keep `check-line`, `stopped-line` (`Failed model: gpt-6-astra — stopped`), `used-taskstop`, `exec-twice`, `two-background-runs`, `two-temp-dirs`, `temp-cleanup`, `no-bare-cd`, the per-run argv graders, `timer-llm`.
- `evals/_harness/ticket-r03-graders.test.mjs` (new, precedent `ticket08-graders.test.mjs`): every new/rewritten regex passes a correct sample (the exact line `stop.sh` prints, taken from `run-stop-scripts.test.mjs`'s shape) and fails: a line missing the `offered:` field, one missing `elapsed`, one with `process tree NOT confirmed` where `ended` is required, a paraphrase, and a trace where the line appears only after `TaskStop`. `codex-call-regex.test.mjs` gains the `run.sh … -- codex exec` shape as a positive sample (the `one-codex-exec`/`exec-twice` regex must still count it as one call).
- Tickets: 03 Comments (rounds, runs, results), 12 (scope correction + "closed offline, live in 04"), 15 and 16 (closed by this slice, with the `--runs 5` numbers), 08 Comments (reliability line: "single green → 2 of 3 → 5 of 5 after this slice").

## Eval plan (sonnet, `--allow-tools Bash Write TaskOutput TaskStop`)

| Step | Cases | Runs | Expect |
|---|---|---|---|
| Offline first | all `evals/_harness/*.test.mjs` (except the pre-existing CRLF failure of `ticket03-patterns`), `claude plugin validate` | — | green |
| Red (unchanged skill, new graders) | `timeout-stalled-stop`, `parallel-shared-timer` | 1 each | fail on `used-stop-script` and the `process tree ended` requirement; other graders as before |
| Green | `timeout-stalled-stop`, `parallel-shared-timer` | **5 each**, `--keep-temp` on the last run of each | all 1.00 |
| Regression | `manual-with-question`, `fail-nonzero-exit`, `followup-carries-claims`, `timeout-alive-notice` | 1 each | 1.00 |

Kept traces: read for the stop order (stop.sh → line → TaskStop → cleanup → restated) and copied to `.scratch/ask-codex-reliability/evidence/03-<case>-trace.jsonl` before the kept directory is deleted (verifier advisory A5 from ticket 08).

## Acceptance

1. Offline checks green; `claude plugin validate` passes; the CODEX_CALL regex counts the prefixed command as exactly one `codex exec`.
2. `timeout-stalled-stop` 5/5 at 1.00 and `parallel-shared-timer` 5/5 at 1.00 on the final skill bytes, with no skill or grader edit after those runs started.
3. In every kept trace the `Consultation stopped:` line printed by `stop.sh` appears verbatim in an assistant text before the `TaskStop` call and again in the final message; in the parallel trace the `done — …; still running — …` fields appear before `TaskStop` (notice, question text or stop report).
4. Regression sample 4/4 at 1.00.
5. Fresh outcome verifier CONFIRMED on the claim "the stop path holds offline: the stub run is ended and verified by the script, and the report is written at the stop and restated, 5 of 5 in both stop cases" — reading the kept traces and rerunning the offline suites.
6. One commit per ticket state change is not required; the slice lands as one commit (rollback: revert it).

## Stops

Any green run below 1.00 after two full-fix passes → pause and report (five passes is the hard budget). A `process tree NOT confirmed` in an eval run is a P1 (script or harness), not a wording issue. Any need to change `run.sh`/`stop.sh` reopens ticket 02's offline test first.
