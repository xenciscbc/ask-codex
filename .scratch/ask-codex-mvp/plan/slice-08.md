# Slice 08 — Parallel consultation (revision 2)

Ticket: `.scratch/ask-codex-mvp/issues/08-parallel-consultation.md` (spec stories 47–49 and the shared-timer story; the ticket cites 36–44, 64). Envelope, lessons (e)–(g) and the eval-grader lessons, stops: `PLAN.md`. Blocked by 03, 04, 07 (all resolved). Serial order: after 06. **Entry gate:** ticket 06's outcome verifier CONFIRMED and recorded. No dollar cap (user decision); 0 live Codex calls.

Revision 2 fixes round 1 (REVISE, 2 blockers): (1) per-model argv graders prove each run carries the full MCP disable set and the invocation contract; (2) the shared timer gets fixed wording with regex graders and a transcript-level check that no half-result is shown and later revised. Advisories taken: per-model wording of the one-exec and Failures rules, a no-cross-talk stdin check, two temp dirs and two background runs counted, fixed refusal wording, a two-model metachar example, and the proactive-parallel narrowing.

## Outcome

- **Two models, manual.** The start of a manual request may name two models separated by a comma, each with an optional effort (`astra:high, sol …`). Each resolves by ticket 03's alias rules and gets its own effort. More than two models, or the same model twice (after resolution), is refused with the fixed line `Parallel consultation takes at most two different models.` and **no `codex` command at all**. A list whose tokens fail ticket 03's validation (e.g. `astra, sol;touch`) is rejected as invalid, also with no `codex` command.
- **Two independent runs.** One background `codex exec` per model, each in its own temp directory (`mktemp -d` twice), with the identical packaged prompt; neither sees the other's output. MCP policy, disable set and guard are computed once and every run carries the full disable set and the full invocation contract. "At most one `codex exec` per consultation" becomes "at most one per model"; no retries.
- **Shared timer (ticket 07).** One interval for both runs. At a check Claude writes the fixed line `Parallel check: done — <slugs or none>; still running — <slugs>.` and asks (or, without `AskUserQuestion`, takes ticket 07's stop fallback) only about runs still going. Finished results are held — no claim is shown before every run has finished or been stopped. Step 10 restates the `Parallel check:` line(s) word for word.
- **Merged presentation** (both succeeded): item 1 names both models and efforts; then the fixed headings `Consensus`, `Solo claims`, `Divergences`; each claim tagged `[gpt-6-astra]`, `[gpt-5.6-sol]` or `[both]` with Claude's disposition; every divergence ends with `Adopted: <slug> — <reason>`.
- **Partial failure or stop.** If one run fails (ticket 04 table) or is stopped (ticket 07), the other's result is presented normally (no grouping) plus the fixed line `Failed model: <slug> — <reason>` (for a stop: `Failed model: <slug> — stopped after <elapsed> without progress`), which replaces a separate stop report for that run. Nothing is attributed to the failed model.
- **Proactive** parallel runs only when a session-scoped override names two models — written in the skill, but not claimed as verified while ticket 05 is paused (recorded in ticket 08 Comments).

## Scope

- `skills/ask/SKILL.md`: step 0 two-model rule and refusals; ground rule and Failures wording per model; steps 1, 7, 8, 9, 11 per model (two temp dirs, same prompt, two background runs, shared timer with the `Parallel check:` line, per-run reply reading, cleanup of both); step 10 merged presentation, restated check lines and the `Failed model:` line.
- `evals/_harness/model-token-rule.mjs` extended (two-model list; three refused; duplicate refused; `astra, sol;touch` invalid; single model and `Why …` unchanged); `ticket03-patterns.test.mjs` extended.
- Stub: `exec.by_model: {"<slug>": {mode, reply, …}}` chooses mode/reply by `-m` (falls back to `exec`); per-call records `exec-argv.<slug>.json`, `exec-stdin.<slug>.txt`; `exec.sentinel` appended per call; `violations.log` unchanged (shared). Existing single-run records stay for other tickets. `stub-modes.test.mjs` extended.
- Cases (Codex-home seeding with ticket 03's HOME guard), generator, `ticket08-graders.test.mjs`, ticket 08 comments, and the case-5 transcript excerpt at `.scratch/ask-codex-mvp/evidence/parallel-shared-timer.txt`.

## Eval cases (runs 1, sonnet; `--allow-tools Bash Write`, plus `TaskOutput TaskStop` for case 5)

**Per-run contract graders** (cases 1, 4, 5; for each `<slug>` in {gpt-6-astra, gpt-5.6-sol}, on `.stub/exec-argv.<slug>.json`): disable definitions `count:5`; `"-s",\s*"read-only"`; `"--disable",\s*"apps"`; plus `no-violations` on `.stub/violations.log`; `mktemp -d` Bash `min 2`; exec Bash with `run_in_background` `min 2` (input_match on the exec command and `"run_in_background":\s*true`).

| # | Case | Prompt start | Stub | Expected | Graders beyond the per-run set |
|---|---|---|---|---|---|
| 1 | `parallel-two-models` | `astra, sol` | by_model: astra reply A, sol reply B (one shared claim, one solo each, one divergence; each reply has a distinctive token) | two runs, merged | exec `min 2 max 2`; astra argv `gpt-6-astra` + `medium`, sol argv `gpt-5.6-sol` + `high`; each stdin contains the question and **not** the other model's distinctive token; last message `Consensus`, `Solo claims`, `Divergences`, `\[gpt-6-astra\]`, `\[gpt-5.6-sol\]`, `Adopted:`; llm: grouping correct, rationale present |
| 2 | `parallel-three-refused` | `astra, sol, terra` | — | refuse | CODEX_CALL `max 0`; no exec sentinel; regex `Parallel consultation takes at most two different models` |
| 3 | `parallel-duplicate-refused` | `sol, 5.6-sol` | — | refuse | CODEX_CALL `max 0`; same regex |
| 4 | `parallel-one-fails` | `astra, sol` | by_model: sol mode `fail` | survivor + note | exec `min 2 max 2`; `Failed model: gpt-5.6-sol`; not_contains `Divergences`; llm: astra presented with dispositions, nothing attributed to sol |
| 5 | `parallel-shared-timer` | `astra, sol` + `EVAL_ASK_CODEX_TIMEOUT_MINUTES=1` | by_model: sol fast valid, astra slow-silent | check: sol done, astra still running → stop astra | `tool_used TaskStop min 1`; regex `Parallel check: done [—-] gpt-5\.6-sol; still running [—-] gpt-6-astra`; `Failed model: gpt-6-astra [—-] stopped`; sol's claims present; run with `--keep-temp`: the assistant texts before the `Parallel check:` line are extracted into the evidence file and must contain no claim ids or `Codex's summary` (checked by the offline test on the extracted file and read by the verifier) |
| 6 | `alias-sol` (ticket-03 regression) | unchanged | | as in 03 | as in 03 |
| 7 | `manual-with-question` (01 regression) | unchanged | | as in 01 | as in 01 |

Offline tests before any paid run: stub by_model and per-call records; the extended reference token rule; every regex grader against a correct reply and a paraphrase or broken variant — headings, tags, `Adopted:`, `Failed model:`, `Parallel check:` (paraphrase fails), refusal line, and an `exec-argv.<slug>.json` missing one disable definition (fails `count:5`).

## Red plan

Cases 1, 2, 4 on the ticket-06 skill.

## Acceptance

1. Offline checks, `claude plugin validate`.
2. Cases 1–7 pass; the case-5 transcript excerpt is committed and shows no claim before the check.
3. SKILL.md has the two-model rule, per-model runs and wording, shared timer with the fixed check line, merged presentation and the `Failed model:` line.
4. Fresh verifier CONFIRMED on the ticket-08 criteria, reading the case-5 transcript excerpt for "no half-result shown and later revised"; proactive two-model parallel narrowed to written text while ticket 05 is paused (recorded).
5. Ticket 08 resolved in one commit (rollback: revert it).
