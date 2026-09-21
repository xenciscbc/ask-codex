# Plan R07b — slice S6b contract: a wait that blocks (ticket 10)

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
- `<n>`: a whole number 1–570 (`^[1-9][0-9]{0,2}$`, ≤ 570); anything else → usage on stderr, exit 2. A missing run directory → message on stderr, exit 2. At least one directory.
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
- New case `evals/headless-timer-stall/`: copy of `evals/timeout-stalled-stop/` (scaffold, case.yaml, graders) with `name: headless-timer-stall`, `tags: [ticket-r10]`, the `prompt.md` front matter of `headless-timer-wait` (same `allowed_tools`, same `append_system_prompt`, own description: the stall path without TaskOutput — the wait script returns `still-running`, the check finds a stale last event, and without `AskUserQuestion` the run is stopped through the stop path), plus `no-taskoutput.md`, `used-wait-script.md`, `no-background-wait.md` (byte-identical copies). Any grader of `timeout-stalled-stop` that REQUIRES a `TaskOutput` call is left out of the copy and named in the report.
- `evals/_harness/ticket-r07-graders.test.mjs`: the count of cases carrying `temp-cleanup` becomes 49.

### 5. Offline tests — `evals/_harness/run-stop-scripts.test.mjs` (extend, same style; must stay green in Git Bash and WSL)
- run.sh writes `exit-code` = `0` after a normal stub run and the command's real non-zero status after a failing one (stub mode `fail`); a stale `exit-code` in the run directory is removed at start; after a stop (`stop.sh`) `exit-code` exists as well.
- wait.sh: returns within 2 s of the run ending with `finished exit=0 <dir>`; on a `slow-silent` run with `--seconds 3` returns after about 3 s with `still-running elapsed=3s <dir>` (allow 3–5) and the run is still alive afterwards; two directories, one finished and one running → two lines in argument order, returns at the time limit; both finished → returns at once; usage errors (`--seconds 0`, `571`, `abc`, missing, no directory, a directory that does not exist) → exit 2 and nothing on stdout; stdout carries nothing but the status lines.
- New `evals/_harness/ticket-r10-skill.test.mjs` (or a group in an existing skill-text test, executor's choice): step 8 contains the new bullet word for word and no longer `start a timer`; `wait for whichever completion notification arrives first` is gone from the file; the three other replaced sentences are present; `SKILL.md` lines 39 and 41 still have the sha256 (first 16 hex) that `evals/_harness/ticket-r07b-s3-graders.test.mjs` pins in `PINNED_LINES` — import nothing, recompute and compare with the literals in that file; the graders of the two headless cases exist and `no-background-wait` fails a trace line with `"command":"sleep 60"` + `"run_in_background":true` and one with `wait.sh` in the background, and passes a foreground `wait.sh` call.

## Ownership

**`executor` owns, exclusively:** `skills/ask/scripts/run.sh`, `skills/ask/scripts/wait.sh` (new), `skills/ask/SKILL.md` (step 8 only), `evals/headless-timer-wait/`, `evals/headless-timer-stall/` (new), `evals/_harness/run-stop-scripts.test.mjs`, the new skill-text test, `evals/_harness/ticket-r07-graders.test.mjs` (the count only). **Must NOT:** run `evals/_harness/run-evals.sh`, `claude plugin eval` or any live eval; commit or stage; touch `stop.sh`, `_tree.sh`, any other case, the READMEs, ADRs or tickets. It may run the offline tests with `node` in Git Bash, and in WSL with `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -ic 'node /mnt/d/work_data/project/skill/ask-codex/evals/_harness/<test>'`. Each shell command its own call; no `cd`.

**Main session owns:** the commit; every live run; `claude plugin validate .`; README (both languages: one sentence under the timeout section that the wait needs no `TaskOutput`), ADR 0004 note, tickets 07 and 10, `CONTEXT.md` glossary if a term is added.

## Done criteria for the executor

`node evals/_harness/run-stop-scripts.test.mjs` green in Git Bash AND in WSL; the new skill-text test, `ticket-r07-graders.test.mjs`, `ticket-r07b-s3-graders.test.mjs`, `ticket-r08-graders.test.mjs` green; `git diff --stat -- skills/ask/SKILL.md` touches step 8 only (report the hunk headers); `git status --porcelain` lists only owned files. Report: files, test outputs on both platforms, hunks, anything that made it stop or deviate.

## Live acceptance (main session), on the committed candidate, fingerprinted run log `evidence/07b-s6b-run-log.txt`

`headless-timer-wait` `--runs 5` and `headless-timer-stall` `--runs 5`, all 1.00; regression `--runs 3` each at 1.00: `timeout-alive-notice`, `timeout-stalled-stop`, `parallel-shared-timer`, `parallel-one-fails` (the TaskOutput path, unchanged text); `manual-with-question` one run. Pass budget: three fix/reverify passes, each with a material change; then the exception rule of `slice-07b.md` section 2. Known before the runs: `parallel-two-models` has an unrelated presentation flake (ticket 13) and is not part of this slice.

## Claim (for the verifier)

On the last S6b commit C: `run.sh` writes `<run dir>/exit-code` on every end and removes a stale one at start; `wait.sh` behaves as specified (offline test green on both platforms); step 8 of `SKILL.md` orders a foreground wait when `TaskOutput` is absent and no longer tells the model to wait for a notification, and no other step changed; the run log shows HEAD = C, a clean tree and one `SKILL.md` sha256 throughout, with both headless cases 5/5 and the four regression cases 3/3 at 1.00; and in the traces of the final pass every `headless-timer-wait` run reads the reply, deletes the run directory and presents C1–C3 in its LAST message, and every `headless-timer-stall` run ends with the `Consultation stopped:` line first, without a `TaskOutput` call in either case.

## Not in this slice

Whether `TaskOutput` exists in current Claude Code versions and whether the skill should prefer the wait script even when it does (one path instead of two) — ticket 10 follow-up. A live headless proof on real Codex like ticket 04's — follow-up, needs a Codex call.
