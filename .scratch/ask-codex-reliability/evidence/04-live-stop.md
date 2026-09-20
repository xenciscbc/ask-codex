# Ticket 04 evidence — the "stopped" guarantee on real Codex

Date: 2026-09-20. Windows 11, Git Bash, `codex-cli 0.154.0` (pnpm shim: `sh.exe → node.exe → codex.exe`). Skill bytes: branch `reliability/stop-path` at `e2e8390` (`skills/` untouched by this ticket). Model `gpt-5.6-luna`, effort `medium` (the user chose the cheap model: the claim is about the process tree, not the answer). `EVAL_ASK_CODEX_TIMEOUT_MINUTES=1` (T = 1 min, S = 10 s). Workspace `D:\tmp\ask-codex-live-04\ws` (a four-file CSV importer). Tooling: `plan/live-04-watch.mjs` (recorder), `plan/live-04-check.mjs` (judge, offline test 27/27), `plan/live-04-extract-reply.mjs` (offline test 10/10).

How to re-check from this directory alone: `node .scratch/ask-codex-reliability/plan/live-04-check.mjs .scratch/ask-codex-reliability/evidence/04-live-<S>-watch.json .scratch/ask-codex-reliability/evidence/04-live-<S>-reply.md` → `exit 0`.

Codex live calls spent: **4** of the 5 allowed in execution — H (pass), I attempt 1 (finished by itself, checker exit 3), H2 (headless trial of the sleep-based stall; Codex's shell tool was down, no stop), I attempt 2 (pass). The verifier's single call is separate.

## Rehearsal (no Codex quota)

A fake chain `sh.exe → node.exe → node.exe` started through the real `run.sh`, stopped with the real `stop.sh`, run directory deleted 3 s later. First attempt: the watcher matched **itself** (with `--leaf node.exe` its own command line carries the marker) — fixed (own pid excluded; the leaf must also carry `-o …/last-message.json`). Second attempt: run directory and root from the pid file, all three members recorded, kill 0.9 s, reported at +7.8 s, quiet window 9.6 s / 38 samples at a constant 772 bytes.

## Scenario H — headless `claude -p`

Command: the README's documented flags (`--permission-mode acceptEdits --allowedTools Bash Read Glob Grep Skill Write TaskOutput TaskStop`) plus `--output-format stream-json --verbose`, prompt `/ask-codex:ask luna Finance says the importer's total is too low … list every defect …`. Run directory `R:\Temp\ask-codex\run.kfBvXh`. Files: `04-live-H-watch.json`, `04-live-H-reply.md`.

| moment | watcher clock | note |
|---|---|---|
| `codex.exe` first seen | 85.2 s | 11:30:44 UTC |
| stop requested (`stop-request` exists) | 158.2 s | the skill's 1-minute check found the last event 49 s old (> S) and, with no `AskUserQuestion`, took "stop" |
| chain gone | 159.6 s | **kill duration 1.4 s** |
| reported (`stop-report` exists) | 166.1 s | after `stop.sh`'s own 5 s window |
| run directory deleted by the skill | 170.7 s | |

Chain recorded (pid, all created 11:30:44–11:31:02 UTC, all last seen at 159.0 s or earlier, i.e. before *reported*): `sh.exe 29984` (root, from the pid file) → `node.exe 732` → `codex.exe 23168` → `codex-code-mode-host.exe 26608`, `codex-windows-sandbox-setup.exe 36484`, `codex-command-runner-0.154.0.exe 29556` → `powershell.exe 33244` → `conhost.exe 30508`.

| check | result |
|---|---|
| chain members alive at +5 s | none |
| chain members alive at +60 s | none |
| `codex.exe` at +60 s vs baseline | 1 vs 1, same pid and creation time |
| `events.jsonl` in the quiet window (chain gone → directory deleted) | **10.8 s, 43 samples, 6113 bytes throughout** |
| `last-message.json` | never appeared |
| reply | `Consultation stopped: interval 1 minutes (override); elapsed 1:13; last event command_execution 0:49 ago; offered: wait another 1 minutes / stop (recommended: stop); process tree ended` — written as the text of the message that calls `TaskStop` (text block 5) and again as the first line of the final reply (block 6) |
| attribution | the final reply says Codex returned nothing and that none of its content comes from Codex; what follows is Claude's own reading of the code |
| checker | `exit 0` |

**A false P1 on the first judgement, and why it is rejected.** The first checker run exited 10: `sleep.exe 34996`, recorded as "child of 29984", was alive after *reported* and beyond the 15 s bound (it was last seen 21 s after the stop request; it was **not** alive at +60 s — `aliveAt60` is empty; an earlier wording of this note said otherwise and was corrected after the outcome verifier's advisory A1). It was created at 11:32:17.8 UTC — **18.8 s after its recorded parent `sh.exe 29984` was last seen** and after the whole chain was gone. A dead process cannot spawn: pid 29984 had been reused by an unrelated shell (the headless session's later Bash calls), and the watcher adopted that shell's `sleep` by parent pid. Disposition: REJECT as a recorder defect, with two fixes, each test-first — the checker excludes a member created more than 2 s after its parent member was last seen (test cases "parent pid reused → excluded" and "child created while its parent was alive and outliving the report → P1"), and the watcher now adopts a child only if its parent is in the same process sample or was in the previous one. The recording itself was **not** edited; the re-judgement used the same file and spent no Codex call. The note is printed by the checker on every run of this file.

Guarded files: `D:\codex\config.toml` byte-identical before and after (`cmp`, sha256 `0be1d229885ef01d…`, mtime 2026-09-19 19:00 — the Codex app was not rewriting it); `C:\Users\admin\.claude\ask-codex.json` absent before and after.

Also seen, outside this ticket's claim: `TaskStop` reported that the task was already gone (the skill calls it anyway, as designed); the reply's model-scope explanation is free prose — the fixed line is ticket 05's.

## Scenario I — interactive session (driven by the user)

`claude --plugin-dir <repo>` started by the user in `D:/tmp/ask-codex-live-04/ws` with `EVAL_ASK_CODEX_TIMEOUT_MINUTES=1`; the watcher ran in the main session. Files: `04-live-I-watch.json`, `04-live-I-reply.md` (extracted from the session transcript `~/.claude/projects/D--tmp-ask-codex-live-04-ws/b0d3dc49-dd1d-4a49-8178-ebc3f99d02a6.jsonl`).

**Skill bytes.** The working tree at the time: `36026d1` plus the uncommitted ticket-08 edits (scenario H ran on `e2e8390`). What the stop path consists of is byte-identical between the two: `git diff e2e8390 -- skills/ask/scripts` is empty, and step 8 (7090 chars) and step 11 of `SKILL.md` are equal after line-ending normalisation.

**Attempt 1 — not a stop (checker exit 3).** Question as in H. At the 1-minute check the last event was 1 s old, so the skill waited; Codex finished by itself 116 s after it started, before the second check. `last-message.json` appeared, no `stop-request`. One call spent, no evidence value for the claim. Seen in passing: the chain of that interactive run included `codex-computer-use.exe` as a child of `codex.exe` (absent in H and in attempt 2) — not investigated here, noted for the MCP-policy owner.

**H2 — a headless trial of a deterministic stall (no stop).** The user's idea: have Codex run `Start-Sleep -Seconds 240` first, so the last event is always older than S at the check. In this trial Codex's shell tool was down (`stderr.log`: six `code-mode host exited during handshake`), it answered in 38 s without reading anything, and the headless Claude ended its turn while the run was still going (ticket 10). Likely cause of the shell failure: the Codex desktop app had been closed in the meantime (no `codex.exe` left on the machine; `config.toml` carries the app's runtime paths). The user reopened it; the app rewrote `config.toml` at 21:39:30, when no ask-codex session was running — changed keys, all app-owned: `notify`, `mcp_servers.node_repl.command`, and `mcp_servers.node_repl.env.{NODE_REPL_NODE_MODULE_DIRS, NODE_REPL_NODE_PATH, NODE_REPL_TRUSTED_CODE_PATHS, BROWSER_USE_CODEX_APP_VERSION, NODE_REPL_TRUSTED_SERVICES, SKY_CUA_NATIVE_PIPE_DIRECTORY, CODEX_CLI_PATH}`; top-level `model` and `model_reasoning_effort` unchanged. Re-baselined from those bytes.

**Attempt 2 — pass.** Question: `luna:high`, "first run `Start-Sleep -Seconds 240` with a command timeout of at least 300 s, then review every function…". Run directory under the interactive session's scratchpad (`R:/Temp/claude/D--tmp-ask-codex-live-04-ws/b0d3dc49-…/scratchpad/ask-codex/run.JIPjhl`).

| moment | watcher clock | note |
|---|---|---|
| `codex.exe` first seen | 225.5 s | |
| stop requested | 306.7 s | at the 1-minute check the last event was `item.started` of the sleeping command, 55 s old; `AskUserQuestion` offered wait / stop (recommended: stop); the user chose stop |
| chain gone | 307.9 s | **kill duration 1.2 s** |
| reported | 315.3 s | |
| run directory deleted by the skill | 321.0 s | |

Chain recorded, all last seen at 307.2 s (before *reported*): `sh.exe 14532` (root, from the pid file) → `node.exe 9852` → `codex.exe 32244` → `codex-code-mode-host.exe 32692`, `codex-command-runner-0.154.0.exe 33408` → `powershell.exe 39636` (**the `Start-Sleep` in progress when the stop came**), `conhost.exe 34404`.

| check | result |
|---|---|
| chain members alive at +5 s / +60 s | none / none |
| `codex.exe` at +60 s vs baseline | 1 vs 1, same pid and creation time (the desktop app) |
| `events.jsonl` in the quiet window | **12.7 s, 50 samples, 904 bytes throughout** |
| `last-message.json` | never appeared |
| reply | the `Consultation stopped: … elapsed 1:22; last event command_execution 1:10 ago; … process tree ended` line is the text of the message that calls `TaskStop` (reply file line 46–47) and the first line of the final answer |
| attribution | "Codex 沒有回覆,以下沒有任何內容來自 Codex"; what follows is Claude's own reading of the code |
| checker | `exit 0`, also when re-run from `evidence/` alone |

Guarded files: `config.toml` byte-identical to the re-baselined copy before and after attempt 2 (and byte-identical across attempt 1 and H2 to the earlier copy); `ask-codex.json` absent throughout. `TaskStop` answered "No task found" — the task had already ended with the tree; the skill calls it regardless, as designed.

## A contract rule that was partly broken, and what it touches

Slice 04 says no eval runs during a live scenario. When the user said "start I", the ticket-08 eval job was running; the main session stopped the outer task and killed the eval then running inside WSL, restored the skill bytes (hash checked) and believed the job was gone. It was not: the outer bash script survived and ran its remaining cases until **21:42:59** local time. Overlap, by scenario: H (19:30) — none, it predates the job; I attempt 1 and the H2 trial — overlapped, and neither is evidence for the claim; **I attempt 2 — the watcher started 21:40:59 (its baseline sample was taken while the last eval case was finishing inside WSL, which starts no Windows `codex.exe`), Codex started 21:44:45 and the stop came 21:46:06, both after the last eval had ended.** The evals run in WSL with a sandboxed `HOME` and a stub `codex`, so they cannot reach `D:codexconfig.toml` or add a Windows `codex.exe`; the guarded-file comparisons above hold regardless.

## Outcome verifier (2026-09-20): CONFIRMED

No headless reproduction was used (Codex calls stay at 4). The verifier recomputed every pass condition from the two watch files, re-extracted both replies from the original session transcripts (byte-identical to the evidence files apart from the header) and matched the transcripts' timestamps to the watcher's moments. Advisories: A1 (P4) a wrong "+60 s" in the note above — corrected; A2 (P3) an empty `D:/tmp/ask-codex-live-04/ws` directory remains because the user's PowerShell window holds it as its working directory — everything in the workspace is deleted, the shell of a directory is removed once the window is closed; A3 (P4) the pid-reuse exclusion could in theory hide a real child if the process sampler stalled for two seconds or more, which the watch file cannot disprove because process samples carry no timestamps — not applicable to H (18 s gap, `events.jsonl` constant), recorded as a possible improvement; A4 **rejected** — the verifier expected the interactive reply's baseline effort to be `medium` from `config.toml`, but step 0 item 1 never uses `model_reasoning_effort` from the config and item 6 gives `gpt-5.6-sol` → `high` when nothing is requested, so "Model baseline: gpt-5.6-sol, effort high (config.toml)" is what the skill prescribes.
