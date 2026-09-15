# Verifier brief — ticket 06 (follow-up consultation)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate = the commit titled "Ticket 06: follow-up consultation" (resolve with `git log --oneline -5`; it follows `e7dece7`, the paused ticket-05 state).
Execution contract: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\slice-06.md` (revision 3 + closing fix, user-approved; repo copy `.scratch/ask-codex-mvp/plan/slice-06.md`). Envelope / lessons: `PLAN.md` in the same directory.
Ticket: `.scratch/ask-codex-mvp/issues/06-follow-up-consultation.md` (criteria + Comments: readiness, entry-gate change, red, green).

## Execution facts to check against

- Red (paused ticket-05 skill): all three ticket-06 cases failed on the new behaviour (no follow-up marker or carried lines; revised plan packaged as a second opinion).
- First green: 4/5; followup-new-blocking wrote the status as C2 `` `[unresolved]` `` and added a note that C5 was omitted. Fixes: the skill says the line starts with the id and bracketed status without backticks or bold, and omitted claims are not mentioned at all; the status regexes tolerate markdown around the id/status (not a different status); case 2 gained a `\bC5\b` not_contains grader; offline samples added (`ticket06-graders.test.mjs` 28/0).
- All five cases (three ticket-06 plus review-loop-blockers and manual-with-question) were then rerun on the final bytes — check timestamps against the last SKILL.md edit and the commit.
- Dollar caps were lifted by the user; ticket 05 is paused (entry-gate change recorded in ticket 06).

## Exact claim to confirm or refute

1. **Who starts a follow-up; type rule.** A follow-up runs on the user's request or as a consented proactive consultation inside a fix or review loop; Claude never starts one on its own elsewhere. Step 0 gives one type rule: follow-up when the conversation holds an earlier consultation's claims about the same question or Plan; otherwise a review-loop consultation is a second opinion (no clash with the Proactive section).
2. **Fresh run and packaging.** Each follow-up is a new ephemeral `codex exec` (no `resume`/`fork`); the prompt uses the follow-up framing (marker, scope lock, `followup_status` rules, new-blocking exception) and carries the claims in the fixed line form `<id> [<disposition>] <statement> — Claude: <reason>`; only the claims that should be carried are carried; the shared core's rule 4 is conditional, so the assembled follow-up prompt has no unconditional `null` instruction while initial prompts keep it.
3. **Presentation.** Each carried claim as `<id> [<status>] … — Updated disposition: …`; missing status shown as `[no status returned]`; new-blocking claims under `New blocking claim from Codex`; non-blocking new claims omitted.
4. **Evidence validity.** `node evals/_harness/ticket06-graders.test.mjs` (incl. prompt assembly) passes; red failed on the new behaviour; green ran on the committed skill bytes; `review-loop-blockers` still yields a second opinion; the ticket-01 regression passes.

## Evidence locations

- `skills/ask/SKILL.md` (step 0, Proactive section, steps 7 and 10), `skills/ask/prompts/consultation.md`, `skills/ask/prompts/framing/follow-up.md`.
- Cases (tag `ticket-06`): followup-carries-claims, followup-new-blocking, followup-revised-plan; regressions review-loop-blockers and manual-with-question.
- Eval results under `evals/results/` from the ticket-06 red runs onward and ticket 06 Comments.

## Allowed reproduction

Static reading; `claude plugin validate`; the offline tests; git inspection. Do not run the real Codex CLI or the paid eval suite.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-claim findings (P0–P4) and evidence.
