# Ticket 01 evidence — stop behaviour probes

Date: 2026-09-18. Codex CLI 0.154.0 (pnpm shim). Workspace `D:\tmp\ask-codex-probe-stop` (deleted at the end). Run directories under `R:\Temp\ask-codex\probe-*` (deleted at the end).

Guarded files before: `D:\codex\config.toml` sha256 `2eb8baef5a5bd4e1…`; `C:\Users\admin\.claude\ask-codex.json` absent.

## Probe A — interactive session, `TaskStop` on the background task

Launched the skill's exact step-8 command (six MCP servers disabled, `--disable apps`, medium effort) with `run_in_background: true` from this interactive Claude Code session. Baseline: `probe-int-baseline.txt` (14 codex/node/sh/bash processes, none from this run).

| t | sh.exe 27996 | node.exe 41752 | codex.exe 25348 | `events.jsonl` bytes |
|---|---|---|---|---|
| +20 s (before stop) | alive | alive | alive | 2 167 |
| `TaskStop` → "Successfully stopped task" | | | | |
| +5 s | alive | alive | alive | 2 710 |
| +60 s | alive | alive | alive | 2 710 |
| +~150 s | gone | gone | gone | 13 011 |

The run **completed on its own after the stop**: `events.jsonl` ends with `turn.completed` (input_tokens 80 975, output_tokens 2 351) and `last-message.json` (9 551 bytes) was written at 09:59. `TaskStop` therefore ended nothing but the harness's task record; the whole chain kept working and spent the full consultation's quota.

**Conclusion A:** the orphaned run happens in the **interactive** session too. Ticket 12's scope statement ("specific to the headless path", based on the single I3 observation) is wrong; the fix must be unconditional and the acceptance must cover both session kinds.

## Probe B — headless session (`claude -p`), same command, `TaskStop` after 20 s

`claude -p` (allowed tools Bash, TaskStop, TaskOutput) was told to start the same command in the background, sleep 20 s, snapshot, `TaskStop`, then snapshot at +5 s and +60 s. Verbatim output in `probe-headless-output.txt`; baseline (8 processes) in `probe-headless-baseline.txt`. The chain from this run was `sh.exe 36396 → node.exe 43208 → codex.exe 32148` (absent from the baseline).

| t | chain | `events.jsonl` bytes |
|---|---|---|
| +20 s (before stop) | alive | 2 092 |
| `TaskStop` → "Successfully stopped task" | | |
| +5 s | alive | 2 092 |
| +60 s | alive | 2 092 |
| after the headless session ended (10:03) | gone | 14 928, `last-message.json` 12 046 bytes written |

Again the run **completed on its own after the stop** (the 60 s of static size was Codex reasoning, not idleness). Identical to the interactive result.

**Conclusion B:** the orphaned run is a property of `TaskStop` on a background Bash task on this platform, independent of session kind. Acceptance for 03/04: verify both session kinds, expect the same behaviour.

## Probe C — tree-kill mechanics (no Codex quota)

- A background job's MSYS pid (`$!`) maps to its Windows pid through the `WINPID` column of Git Bash `ps` (`ps | awk -v p=$! '$1==p {print $4}'`).
- `bash -c 'node …' &` execs node directly (single command), so `$!` mapped straight to `node.exe`; `taskkill //T //F //PID <winpid>` killed it.
- Four-level chain `sh.exe → sh.exe → node.exe → node.exe` (built with `sh -c 'node -e "spawn(node …)"'`): `taskkill //T //F` on the top Windows pid terminated all four (taskkill reported each child, a `Get-CimInstance` walk afterwards found none).

**Conclusion C:** on Windows the stop script can record `$!`, map it to a Windows pid via `ps`, and rely on `taskkill /T /F` to end the pnpm shim → node → codex.exe chain. Enumerating the tree by `ParentProcessId` from the recorded pid is a workable post-kill verification.

## Probe D — `timeout-stalled-stop --keep-temp --runs 3` (stop-report gap)

Run after the reboot (WSL networking came back by itself). Results `evals/results/2026-09-18T02-30-38-949Z/`, traces read from the kept sandboxes `/tmp/ask-codex-eval.JfFzd0/tmp/claude-eval-{T0ud7T,Dq36wN,zasEBE}/out/trace.jsonl` (deleted afterwards). Scores: run 0 1.00, runs 1 and 2 0.86 — `stopped-line` (regex) passed in all three, `stop-report` (LLM judge, three votes) failed 3–0 in runs 1 and 2.

Where `Consultation stopped:` appears, per run (assistant text blocks numbered in order):

| run | sandbox | blocks | stop-moment message | `TaskStop` | report line |
|---|---|---|---|---|---|
| 0 | T0ud7T | 11 | [9] describes the stale run, **no report line** | after [9] | [11] only — the final message |
| 1 | Dq36wN | 13 | [11] describes the stale run, **no report line** | after [11] | [13] only — the final message |
| 2 | zasEBE | 9 | [7] describes the stale run, **no report line** | after [7] | [9] only — the final message |

So in this sample the report is **never written at the moment of the stop**; it is composed once, free-form, in the final presentation (step 10), after the cleanup. The two judged failures are field gaps in that free-form line: run 1 never states the two offered options, and run 2 reports the elapsed time as "~73+ seconds … past the 1-minute window" mixed with an unrelated remark about `-m`, while run 0 states everything. The ticket-16 shape ("no report at all", 1 in 3) did not recur here; the shape that did recur (2 in 3) is "written once at the end, with fields missing or muddled".

**Conclusion D:** the gap is "not written at the stop, and improvised at the end" rather than "written mid-run and not restated". Both halves of the spec's remedy apply: the stop script prints the complete fixed line so the fields cannot be improvised, and the skill copies it verbatim twice — in the message that stops the run and again in step 10. Ticket 03's `stopped-line` grader should also require the line at the stop moment (a `target: trace` regex), not only in the final response.

## Probe E — `second-opinion-with-stance --keep-temp --runs 5` (bare `cd`)

Results `evals/results/2026-09-18T02-40-04-451Z/`: **5 of 5 runs 1.00**, every grader passed including `no-bare-cd`. The five kept traces (`/tmp/ask-codex-eval.nGP721/tmp/claude-eval-{FOlqtY,DH6zEr,sZTxKM,JkEP74,bSusXX}`, deleted afterwards) were scanned for every Bash call: 12, 12, 14, 13 and 11 calls per run, and **no command in any form starting with `cd`** — neither as the first token nor after `;`, `&&`, `|`, `(` or a newline.

**Conclusion E:** not reproduced in five runs. Ticket 17's single observation stands as a one-off; ticket 06 should be a wording guard plus the existing `no-bare-cd` grader (already 5/5 here), not a behavioural fix with a red phase — there is nothing to turn red.

## Guarded files after all probes

- `C:\Users\admin\.claude\ask-codex.json`: still absent.
- `D:\codex\config.toml`: sha256 now `3cd8577077cee9a4…`, **different** from the `2eb8baef5a5bd4e1…` recorded before probes A–C and re-verified at 10:24 today (after the reboot, before anything was launched). The file's mtime is **10:29:39**, which is when the Codex desktop app came up after the reboot (`codex.exe` started 10:28:55); probe D was launched at 10:30 and both probes run inside WSL with a sandboxed `HOME`, so they cannot reach `D:\codex`. The change is therefore the app's own rewrite (the known runtime-path / pipe-GUID / app-version fields), not the skill's. The per-field list required by the ticket cannot be produced because no copy of the earlier bytes exists — only the hash was recorded. Top-level `model = "gpt-6-astra"` and `model_reasoning_effort = "medium"` are the current values; whether `model` was rewritten cannot be told from a hash. **Lesson for ticket 04:** back up `config.toml` bytes (not just the hash) before each live scenario, and take the hash only once the Codex app has finished starting.

## Cleanup

Probe workspace `D:\tmp\ask-codex-probe-stop` and the `R:\Temp\ask-codex\probe-*` run directories were deleted in the first session; both kept eval sandboxes (`/tmp/ask-codex-eval.JfFzd0`, `/tmp/ask-codex-eval.nGP721`) were deleted after their traces were read; the harness's own cleanup removed `.eval-stub/` and every `stubbin/`. No skill, eval or README file was changed by this ticket.
