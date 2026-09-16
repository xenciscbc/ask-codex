# 12 — Stopping a consultation leaves Codex running

**What to build:** when a consultation is stopped — by the stall question, by the non-interactive stop rule, or by the user — the Codex process chain it started actually ends. Today the skill calls `TaskStop` and reports `Consultation stopped:`, but on Windows the `codex.exe` it spawned keeps running: it continues reading files, keeps writing `events.jsonl`, and keeps spending API quota, while the user has been told the consultation is over.

**Blocked by:** None — can start immediately (found during ticket 09 live acceptance; ticket 09 records F8 as failing because of it).

**Status:** ready-for-agent

## Evidence (ticket 09, 2026-09-16)

- **A8** (the skill's own stop path, headless, `EVAL_ASK_CODEX_TIMEOUT_MINUTES=1`): the skill detected the stall correctly, called `TaskStop`, and reported the stop. Its own snapshot ~5 s later showed three `codex` processes alive that were absent from the pre-run baseline (PIDs 49108, 31216, 13432, `@openai+codex@0.154.0`). They were still alive minutes later.
- **A8b** (direct probe, same stop mechanism): `TaskStop` returned `Successfully stopped task`, yet the whole tree survived at +5 s and +75 s — `sh.exe → node.exe` (the pnpm shim) `→ codex.exe`, the last carrying exactly the argv that was sent. `events.jsonl` grew from 788 to 2579 bytes *after* the stop, so the consultation was still working; `last-message.json` never appeared. The chain only ended when killed with `Stop-Process -Force`.
- Cause: `TaskStop` ends the harness's task (and its shell), but the `codex.exe` grandchild launched through the pnpm shim is not part of what gets killed.

## Acceptance criteria

- [ ] After a stop, no `codex` process that was absent from a baseline taken before the run remains — verified by a snapshot taken inside the still-running session, a few seconds after the stop.
- [ ] The stop path kills the process tree, not just the task: on Windows via the equivalent of `taskkill /T /F /PID <pid>` for the shell it started, elsewhere via a process-group kill; the skill records the pid when it launches the run so it has something to kill.
- [ ] The stop report is only written after the kill has been verified; if a process survives, the report says so instead of claiming the consultation was stopped.
- [ ] `events.jsonl` stops growing after the stop (the check that proves the run is not merely orphaned but genuinely ended).
- [ ] An eval covers it offline: the stub's `slow-silent` mode plus a grader asserting the kill command follows `TaskStop` in the trace, since the process check itself cannot run in the eval sandbox.
- [ ] The README's timeout section states the guarantee that actually holds after the fix.
