# Verifier brief — ticket 07 (timeout monitoring)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate = the commit titled "Ticket 07: timeout monitoring" (resolve with `git log --oneline -5`).
Execution contract: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\slice-07.md` (revision 3 + closing fix, user-approved). Envelope / F-map (F8, F11) / budget: `PLAN.md` in the same directory.
Ticket: `.scratch/ask-codex-mvp/issues/07-timeout-monitoring.md` (criteria + Comments: readiness, tool probe and chosen route, red, green).

## Execution facts to check against

- Route 1 of the slice's route table (tool probe `task-tools-probe` 1.0: `TaskOutput` and `TaskStop` usable with `--allow-tools Bash Write TaskOutput TaskStop`, the same grant as every ticket-07 run; `bg-notify-probe` not needed).
- Tightening after ticket 04's verifier: each notice uses fixed wording (`Timeout override active:`, `Timeout override ignored:`, `Codex still running`, `Consultation stopped:`) checked by last-message regex graders next to the llm graders; `node evals/_harness/ticket07-graders.test.mjs` shows each pattern fails a paraphrase without the wording.
- The first green pass had one miss (timeout-override-invalid-zero folded the ignored-override line into a sentence); step 10 was tightened and all five cases rerun. In that rerun invalid-zero failed again: the agent skipped step-11 cleanup, and the llm grader's "first item" wording failed a reply that opened with a warning about Codex citing files absent from the ticket-07 scaffold. Fixes: the ticket-07 cases now use the ticket-01 workspace (retry loop + `src/pages/profile.js`, matching the stub's default reply), the llm graders no longer require the "first item" position (regex graders keep the fixed wording), and step 10 ends with an explicit "run step 11 before answering" reminder. **All five cases were then rerun on the final bytes** — check the rerun timestamps against the SKILL.md edit time and the commit, and judge whether the skipped cleanup is fixed or merely not reproduced (n = 1 per case).
- Dollar caps were lifted by the user (Claude subscription; completion first); spend is logged only.

## Exact claim to confirm or refute (per the route recorded in ticket 07)

1. **Timer and liveness.** Step 8 checks every interval T (default 30 min; `EVAL_ASK_CODEX_TIMEOUT_MINUTES` positive integer overrides it; S = T/6); liveness is judged only from the tracked task state and the last-event age of `events.jsonl` (no CPU/process listings); confirmed → one-line notice, keep waiting, no question; not confirmed → the wait/stop question with elapsed time, last event and age, recommendation by the T/2 rule; no cap on waiting.
2. **Non-interactive fallback and stop.** Without `AskUserQuestion` the question is stated in text and "stop" is taken; stop ends the tracked task (`TaskStop`), follows Failures (nothing attributed to Codex, cleanup, carry on) and gives a final stop report with the required fields.
3. **F11.** Zero, negative, non-numeric overrides are ignored with a notice (default used); a valid override shows that it is active; the timer outcome is restated in the final answer's first item.
4. **Evidence validity.** The tool probe (and, if run, the notification probe) used the same `--allow-tools` grant as the cases; the route table was applied; red failed on the new behaviour; green ran on the committed skill bytes; no "not granted" notices for the tools the route uses.
Not in the claim: F8 process-chain termination and the interactive `AskUserQuestion` branch (ticket 09 live acceptance).

## Evidence locations

- `skills/ask/SKILL.md` (step 8, Failures, step 10 item 1), `evals/_harness/stub/codex-stub.py` (slow modes), `evals/_harness/stub-modes.test.mjs`.
- Cases (tag `ticket-07`): timeout-alive-notice, timeout-stalled-stop, timeout-override-invalid-text, timeout-override-invalid-zero, task-tools-probe (and bg-notify-probe if run); regression manual-with-question.
- Eval results under `evals/results/` from the ticket-07 probe onward and ticket 07 Comments.

## Allowed reproduction

Static reading; `claude plugin validate`; the offline tests; git inspection; stub probes in a temp dir under `D:\tmp` (delete afterwards; slow modes with short durations). Do not run the real Codex CLI or the paid eval suite.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-claim findings (P0–P4) and evidence.
