# Plan R07b — slice S6b contract (revision 3, readiness epoch 2): a wait that blocks (ticket 10)

Readiness history: revision 1 REVISE (design found sound; acceptance demanded 1.00 on graders with a recorded miss rate; the TaskOutput simulation measured on one run, no rule for a failed simulation) → revision 2 REVISE (five P2, all in the acceptance rules: the NEW stall case borrowed another case's excuses; LLM-judge rule covered split votes only and collided with a second row; no kept traces for a trace-level claim; an uncapped case-design rerun; `no-bare-cd` unnamed for one case and no route for a miss caused outside the slice). All seven dispositioned FIX: the acceptance section is rewritten as rules R1–R5 and the stall case no longer copies the two graders it cannot answer for. One closing review follows.

Added to Plan R07b by user decision on 2026-09-21, after S6 reproduced ticket 10. The Plan's S6 allowed "a wording change in step 8 'Waiting'"; this goes further (two scripts and the step's text), so it is its own slice with its own review. One-shot execution contract for `executor`. Not security-sensitive: no confirmation, credential or sandbox rule is touched; risk trigger "material cross-component acceptance" (skill text + scripts + evals) → slice review before, outcome `verifier` after.

## The defect (evidence)

`evals/headless-timer-wait` (TaskOutput's absence simulated by `append_system_prompt`; the harness cannot withhold the tool — commit `7d58a90`), trace `.scratch/ask-codex-reliability/evidence/07b-traces/headless-timer-wait-REzas1-turn-ended-while-waiting.jsonl`: the model starts Codex in the background, starts `sleep 60` in the background, writes `Now waiting for either the Codex consultation or the 1-minute timer to complete.` — and the turn ends. No step 9, 10 or 11; the run directory with `prompt.md` stays on disk. Same as the live incident of ticket 10 (`issues/10-headless-turn-ended-while-consultation-running.md`).

Cause: `skills/ask/SKILL.md` step 8, "Waiting", second bullet — "Otherwise start a timer — `sleep <T in seconds>` with Bash `run_in_background: true` — and wait for whichever completion notification arrives first". A model cannot wait without a blocking tool call: when it stops calling tools the turn ends. In an interactive session the completion notification starts a new turn; in a non-interactive one nothing does, although the same step says "Do not end your turn while the consultation is still running". `scripts/run.sh` leaves no marker when the command ends normally, so there is nothing to block on. In current Claude Code sessions `TaskOutput` may not exist at all (in the main session of 2026-09-21 ToolSearch did not find it), so this "fallback" can be the only path.

## Goal

Without `TaskOutput`, step 8 waits with a FOREGROUND command that returns when the consultation has ended or the time is up, so the turn never ends while Codex runs; steps 9–11 follow in the same turn; the liveness check, the stop path and parallel consultations work on that path too. With `TaskOutput`, nothing changes.

## Changes

### 1. `skills/ask/scripts/run.sh`
- At start, next to the existing `rm -f …stop-request …stop-result`: also remove `"$run_dir/exit-code"`.
- After `wait "$child"; status=$?` (before the stop-request block): write the status, atomically — `printf '%s\n' "$status" > "$run_dir/exit-code.tmp" && mv -f "$run_dir/exit-code.tmp" "$run_dir/exit-code"`. Written on every end, including after a stop request. Nothing else in the file changes; its exit status stays `$status`.

### 2. New `skills/ask/scripts/wait.sh`
`bash wait.sh <run directory> [<run directory> …] --seconds <n>` — blocks in the foreground until EVERY named run directory has an `exit-code` file or `<n>` seconds have passed, whichever comes first; file-based only (in the eval sandbox every Bash call is its own PID namespace, so pids mean nothing across calls).
- Argument order is fixed: one or more run directories first, then `--seconds <n>` last; anything else → usage on stderr, exit 2.
- `<n>`: a whole number 1–570 (`^[1-9][0-9]{0,2}$`, ≤ 570); anything else → usage on stderr, exit 2. A missing run directory → message on stderr, exit 2. At least one directory.
- `still-running` cannot tell "still running" from "`run.sh` died without writing `exit-code`" (killed, or a usage error before the launch). That is accepted: `events.jsonl` then stops changing and step 8's check leads to the stop path one interval later. Say so in the header comment.
- Polls once a second (`sleep 1`); no busy loop, no `wait`/`kill -0` on pids.
- Output: exactly one line per run directory, in argument order, on stdout, and nothing else: `finished exit=<code> <run directory>` or `still-running elapsed=<seconds>s <run directory>`. Exit status 0 in both cases.
- Style, header comment, `set -u` conventions and quoting as in `run.sh`/`stop.sh`; every path quoted; works in Git Bash and WSL bash.

### 3. `skills/ask/SKILL.md`, step 8 only (every other step byte-identical; lines 39 and 41 in particular)
(a) Replace the second bullet of "**Waiting.**" — the one beginning `- Otherwise start a timer` — with exactly:

```
- Otherwise wait with the wait script, in the **foreground** — never start a timer in the background and "wait for a notification": your turn ends the moment you stop calling tools, and in a non-interactive session nothing brings you back, so Codex would finish unread and the run directory would stay behind. One line, literal single-quoted paths, Bash `timeout: 600000`: `bash '<skill directory>/scripts/wait.sh' '<tmp>' --seconds <n>` where `<n>` is the time left in the interval in seconds, at most 540 (the Bash tool itself stops a command after 10 minutes). It prints `finished exit=<code> <tmp>` or `still-running elapsed=<n>s <tmp>`; while it prints `still-running` and T has not passed, run it again.
```

(b) In "**Check when T has passed.**", the sentence `Judge liveness only from the tracked task's state and the last event in \`<tmp>/events.jsonl\` — never from CPU use or process listings:` becomes `Judge liveness only from the tracked task's state — without \`TaskOutput\`, from the wait script's line — and the last event in \`<tmp>/events.jsonl\` — never from CPU use or process listings:`.

(c) In "**Parallel consultation.**", the sentence `Both share one timer.` becomes `Both share one interval; without \`TaskOutput\`, name both run directories in one wait command (\`… wait.sh '<tmp1>' '<tmp2>' --seconds <n>\`), which returns when both have finished or the time is up.`

(d) The run.sh paragraph ("The `run.sh` prefix ships with this skill: it starts Codex as its own process tree and writes `<tmp>/pid` so the stop script can end it; …"): after `so the stop script can end it` insert `, and \`<tmp>/exit-code\` when the command ends so the wait script can see it`.

If a sentence to replace does not occur exactly once in step 8, the executor stops and reports.

### 4. Evals
- `evals/headless-timer-wait/graders/used-background-timer.md` → delete; new `used-wait-script.md`: `tool_used`, `tool: Bash`, `input_match: 'scripts/wait\.sh'`, `min: 1`; new `no-background-wait.md`: `tool_used`, `tool: Bash`, `input_match: '(?=.*(?:scripts/wait\.sh|"command"\s*:\s*"sleep\s+[0-9]+))(?=.*"run_in_background"\s*:\s*true)'`, `min: 0`, `max: 0` (neither the wait script nor a bare `sleep` timer in the background). Update the description in `prompt.md` only if it mentions the background timer as the expected behaviour (it may say "the wait without TaskOutput").
- New case `evals/headless-timer-stall/`: `name: headless-timer-stall`, `tags: [ticket-r10]`; `scaffold.sh` and `case.yaml` copied from `evals/timeout-stalled-stop/`; the `prompt.md` front matter of `headless-timer-wait` (same `allowed_tools`, same `append_system_prompt`, own description: the stall path without TaskOutput — the wait script returns `still-running`, the check finds a stale last event, and without `AskUserQuestion` the run is stopped through the stop path). Graders — copied byte for byte from `timeout-stalled-stop`: `skill-fired`, `one-codex-exec`, `used-run-script`, `used-stop-script`, `used-taskstop`, `temp-cleanup`, `no-bare-cd`, `stopped-line`; copied from `headless-timer-wait`: `no-taskoutput`, `used-wait-script`, `no-background-wait`; NOT copied: `stopped-at-stop`, `stop-report` (see rule R3); new `final-has-stopped-line.md` — `type: regex`, last message, pattern `Consultation stopped:[\s\S]*process tree ended` (a backslash-s backslash-S class, as in `evals/headless-timer-wait/graders/final-presents-claims.md`) — the stop line is in the final answer at all (every field is `stopped-line`'s job). The offline skill-text test asserts that this grader PASSES a real stop line of the shape in `evals/timeout-stalled-stop/graders/stopped-line.md` (for example `Consultation stopped: interval 1 minutes (override); elapsed 1:12; last event turn.started 1:10 ago; offered: wait another 1 minutes / stop (recommended: stop); process tree ended`, also with markdown emphasis and with the model's own answer below it) and FAILS a reply without it and one that ends `process tree NOT confirmed — pids 123`.
- `evals/_harness/ticket-r07-graders.test.mjs`: the count of cases carrying `temp-cleanup` becomes 49.

### 5. Offline tests — `evals/_harness/run-stop-scripts.test.mjs` (extend, same style; must stay green in Git Bash and WSL)
- run.sh writes `exit-code` = `0` after a normal stub run and the command's real non-zero status after a failing one (stub mode `fail`); a stale `exit-code` in the run directory is removed at start; after a stop (`stop.sh`) `exit-code` exists as well.
- wait.sh: returns within 2 s of the run ending with `finished exit=0 <dir>`; on a `slow-silent` run with `--seconds 3` returns after about 3 s with `still-running elapsed=3s <dir>` (allow 3–5) and the run is still alive afterwards; two directories, one finished and one running → two lines in argument order, returns at the time limit; both finished → returns at once; usage errors (`--seconds 0`, `571`, `abc`, missing, `--seconds` before the directories, no directory, a directory that does not exist) → exit 2 and nothing on stdout; on both normal outcomes (`finished`, `still-running`) the exit status is 0 — assert it; stdout carries nothing but the status lines.
- New `evals/_harness/ticket-r10-skill.test.mjs` (or a group in an existing skill-text test, executor's choice): step 8 contains the new bullet word for word and no longer `start a timer`; `wait for whichever completion notification arrives first` is gone from the file; the three other replaced sentences are present; `SKILL.md` lines 39 and 41 still have the sha256 (first 16 hex) that `evals/_harness/ticket-r07b-s3-graders.test.mjs` pins in `PINNED_LINES` — import nothing, recompute and compare with the literals in that file; the graders of the two headless cases exist and `no-background-wait` fails a trace line with `"command":"sleep 60"` + `"run_in_background":true` and one with `wait.sh` in the background, and passes a foreground `wait.sh` call.

## Ownership

**`executor` owns, exclusively:** `skills/ask/scripts/run.sh`, `skills/ask/scripts/wait.sh` (new), `skills/ask/SKILL.md` (step 8 only), `evals/headless-timer-wait/`, `evals/headless-timer-stall/` (new), `evals/_harness/run-stop-scripts.test.mjs`, the new skill-text test, `evals/_harness/ticket-r07-graders.test.mjs` (the count only). **Must NOT:** run `evals/_harness/run-evals.sh`, `claude plugin eval` or any live eval; commit or stage; touch `stop.sh`, `_tree.sh`, any other case, the READMEs, ADRs or tickets. It may run the offline tests with `node` in Git Bash, and in WSL with `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -ic 'node /mnt/d/work_data/project/skill/ask-codex/evals/_harness/<test>'`. Each shell command its own call; no `cd`.

**Main session owns:** the commit; every live run; `claude plugin validate .`; README (both languages: one sentence under the timeout section that the wait needs no `TaskOutput`), ADR 0004 note, tickets 07 and 10, `CONTEXT.md` glossary if a term is added.

## Done criteria for the executor

`node evals/_harness/run-stop-scripts.test.mjs` green in Git Bash AND in WSL; the new skill-text test, `ticket-r07-graders.test.mjs`, `ticket-r07b-s3-graders.test.mjs`, `ticket-r08-graders.test.mjs` green; `git diff --stat -- skills/ask/SKILL.md` touches step 8 only (report the hunk headers); `git status --porcelain` lists only owned files. Report: files, test outputs on both platforms, hunks, anything that made it stop or deviate.

## Live acceptance (main session), on the committed candidate

Runner: `plan/r07b-run-logged.sh` (it runs with `--keep-temp` and copies every trace to `D:\tmp\ask-codex-r07b-traces\s6b-<case>\`); fingerprinted run log `evidence/07b-s6b-run-log.txt`, EVERY pass appended, none deleted. After the final pass the main session copies the traces of every counted headless run into `evidence/07b-s6b-traces/` and lists the file names in ticket 10. From the executor's handover on, the two headless case directories belong to the main session.

Runs of a pass: `headless-timer-wait` `--runs 5`, `headless-timer-stall` `--runs 5`; regression `--runs 3` each: `timeout-alive-notice`, `timeout-stalled-stop`, `parallel-shared-timer`, `parallel-one-fails` (the text of the TaskOutput branch is unchanged; the two parallel cases also read the reworded "Parallel consultation" sentence); `manual-with-question` one run. Only the FINAL pass decides.

### Rules — a verdict for any result, from this text alone

**R1 — counted runs.** `TaskOutput`'s absence is simulated by `append_system_prompt` (measured: 1 run on `7d58a90`, no `TaskOutput` call; before that form 10 of 10 runs called it). A headless run in which `no-taskoutput` fails did not take the path under test: it is NOT counted, for or against. A headless case needs at least 4 counted runs in the final pass. With fewer, the main session may strengthen the appended sentence — a change to the case, never to the skill — and rerun that case ONCE per case in the whole slice; still fewer than 4 → pause, exception rule of `slice-07b.md` section 2. All bounds below are COUNTS ("at most 1 miss"), whether 4 or 5 runs are counted.

**R2 — must be 1.00 in every counted run, no exception.** `headless-timer-wait`: `used-wait-script`, `no-background-wait`, `final-mcp-line`, `final-presents-claims`, `temp-cleanup`, `one-codex-exec`, `exec-sentinel`, `no-violations`, `skill-fired`. `headless-timer-stall`: `used-wait-script`, `no-background-wait`, `used-run-script`, `used-stop-script`, `used-taskstop`, `final-has-stopped-line`, `temp-cleanup`, `one-codex-exec`, `skill-fired`. A miss here is an S6b finding: it consumes a fix pass if its cause lies in a file this slice owns; otherwise R5.

**R3 — named graders with a recorded history (deterministic).** A miss is recorded, not attributed to S6b and consumes no pass, only within these bounds; above a bound → pause, exception rule, no skill edit:
- `no-bare-cd` in `headless-timer-wait`, `headless-timer-stall`, `timeout-stalled-stop`: at most 1 miss per case, and only if the trace shows the `cd` in root discovery (`cd … && git rev-parse`, tickets 06/17 — recorded 1/15, `issues/03-…md:40`); a `cd` anywhere else counts under R2.
- `override-active` in `headless-timer-wait`: at most 1 miss (1 in 5 recorded on the predecessor bytes, `evidence/07b-s6-run-log.txt` run 4).
- `stopped-line` (all fields) in `headless-timer-stall`: at most 1 miss, and only if `final-has-stopped-line` passed in that run (the line is there, a field is paraphrased — the recorded 14/15 family); if `final-has-stopped-line` failed too, it is an R2 miss.
- `stopped-at-stop` and `stopped-line` in `timeout-stalled-stop` (3 runs): at most 1 miss each (recorded 12/15 and 14/15, accepted by the user 2026-09-18, `issues/03-…md:24,27,40`).
`headless-timer-stall` does NOT carry `stopped-at-stop` or `stop-report`: the first records a behaviour this slice does not touch (a `TaskStop` call in a message without text) and the new case has no history of its own to excuse a miss with; the second is an LLM judge.

**R4 — LLM judges (one rule, any vote split; `stop-report` of `timeout-stalled-stop` and `timer-llm` of `parallel-shared-timer` are governed by this rule only).** At most 1 miss per case in its 3 runs; then that case is rerun once `--runs 3`, and any LLM-judge miss in the rerun → pause, exception rule. Two or more misses in the first 3 runs → pause at once. The main session reads the failed reply either way and records whether it meets the rubric.

**R5 — a miss whose cause, read from the trace, lies outside the files this slice owns** (a grader or fixture defect of an untouched case, a harness fault): exception rule; it consumes no fix pass and the skill is not edited for it.

**R6 — the regression cases.** In `timeout-alive-notice`, `timeout-stalled-stop`, `parallel-shared-timer`, `parallel-one-fails` and `manual-with-question`, every grader NOT named in R3 and not an LLM judge (R4) must be 1.00 in every run of the final pass — for example `used-stop-script`, `used-taskstop`, `used-run-script`, `still-running`, `check-line`, `parallel-info-before-stop`, `temp-cleanup`. A miss whose cause, read from the trace, is one of this slice's changes (step 8's four sentences, `run.sh`, `wait.sh`) is an S6b defect and consumes a fix pass; any other cause → R5. `manual-with-question` runs once: a miss of its LLM judge `dispositions` is handled by R4 with "rerun once `--runs 3`" applied to that single run.

**R7 — the fingerprint of the final pass.** What is fixed is the skill: one `skills/ask/SKILL.md` sha256 and an empty `git diff <first commit of the pass>..<last> -- skills` for every invocation of the final pass, each with a clean tree. If R1's case-design rerun changes a headless case's `prompt.md`, that change is its own commit C2 touching only that case directory; the runs of the OTHER cases made at C stay part of the final pass, and the rerun case's runs at C2 replace its runs at C. The run log shows both commits; the claim's "C" is then the pair (C, C2) with identical `skills/` bytes.

Pass budget: three fix/reverify passes, each with a material change to the skill's step 8, the two scripts, or this slice's own case and grader files (a defect in one of those — a wrong pattern, a wrong scenario — is fixed there and costs a pass like any other; R1's case-design rerun is the one exception). Expected eval spend about USD 20 (about 22 runs per pass). Known before the runs: `parallel-two-models` has an unrelated presentation flake (ticket 13) and is not part of this slice.

## Claim (for the verifier)

On the last S6b commit C: `run.sh` writes `<run dir>/exit-code` on every end of the launched command, including after a stop request, and removes a stale one at start when its arguments are valid (it cannot write one when `run.sh` itself exits on a usage error or is killed — then `wait.sh` reports `still-running`, `events.jsonl` goes stale and one interval later the check leads to the stop path; bounded, recorded); `wait.sh` behaves as specified (offline test green on both platforms); step 8 of `SKILL.md` orders a foreground wait when `TaskOutput` is absent and no longer tells the model to wait for a notification, and no other step changed; the run log shows, for the final pass, the fingerprint of rule R7 (HEAD = C — or the pair C, C2 of R7 — a clean tree and one `SKILL.md` sha256 throughout); the final pass meets rules R1–R7 — the two headless cases AND the five regression cases (R6) — with every named miss listed with its rule; and the traces in `evidence/07b-s6b-traces/` show that every counted `headless-timer-wait` run waits with `wait.sh` in the foreground, reads `last-message.json`, issues the `rm -rf` of its run directory and presents C1–C3 in its LAST message, and that every counted `headless-timer-stall` run reaches the stop path through `stop.sh` and `TaskStop`, issues the cleanup and has `Consultation stopped:` … `process tree ended` in its last message.

The main session also corrects Outcome (5) of `slice-07b.md` ("runs the background-timer wait" becomes "waits in the foreground without `TaskOutput`") in the record commit of this slice.

## Not in this slice

Whether `TaskOutput` exists in current Claude Code versions and whether the skill should prefer the wait script even when it does (one path instead of two) — ticket 10 follow-up. A live headless proof on real Codex like ticket 04's — follow-up, needs a Codex call.
