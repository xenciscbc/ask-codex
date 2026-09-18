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

## Probe D — `timeout-stalled-stop` with `--keep-temp` (stop-report gap)

_Blocked: WSL networking failed at VM creation (`ConfigureNetworking/0x8007054f`, fell back to `networkingMode None`), so the eval harness cannot reach the API. Pending the user's decision on the WSL fix._

## Probe E — `second-opinion-with-stance` `--keep-temp --runs 5` (bare `cd`)

_Blocked on the same WSL issue._
