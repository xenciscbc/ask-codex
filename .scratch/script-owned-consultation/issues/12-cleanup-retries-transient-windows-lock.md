# 12: Cleanup survives a transient Windows file lock after a run ends

**What to build:** `remove_run` (`skills/ask/scripts/consult.py:142`) deletes a finished run directory with a single `shutil.rmtree` / `unlink` pass. On Windows, a handle to a run file can stay open for a short time after the run ends. When that happens, deletion fails with `PermissionError` (WinError 32). `collect` then reports `cleanup_failed`, even though the reply was delivered. Deletion should survive a lock that clears within a short, bounded time. A lock that does not clear still ends in `cleanup_failed` with `retained_location`, as it does today.

**Blocked by:** None (can start immediately).

Status: resolved — bounded retry in remove_run plus harness fix (2026-09-25)

## Evidence

- **Live, 2026-09-25, after the v1.1.1 push.** Real consultation on Codex CLI 0.156.1, `gpt-6-sol` high, base `D:\tmp\ac-live`.
  - `collect` returned the structured reply, exit 0, then printed `{"state": "cleanup_failed", "retained_location": ...}`.
  - An immediate `cleanup` also failed, with `PermissionError: consultation operation failed`.
  - About a minute later, every run file opened with exclusive access, and no process's command line referenced the run.
  - A second `cleanup` then returned `cleaned`.
- **Suite.** `test_partial_parallel_launch_failure_stops_started_consultation` fails on `main` with the same class of error (WinError 32 on `0/events.jsonl` during test cleanup). It failed on `6efee99` and on `adb3a16` alike, so the failure predates v1.1.1. It is probably the same cause, but that has not been confirmed.
- **Also seen, 2026-09-25, cause not yet known.** `cleanup` failed with `OSError` on a run under the R: RAM disk, with a base under the scratchpad. That run was only prepared, never started. It may be a different issue.

## Acceptance

- [x] A lock that is released within a bounded time does not fail `collect` or `cleanup`, and that time stays well inside the Bash tool's timeout.
- [x] A lock that is not released still yields `cleanup_failed` with `retained_location`. The reply is never lost, and a later `cleanup` can finish the job.
- [x] Deletion never goes past the run directory, and `plan.json` is still removed last.
- [x] An offline test reproduces a lock that is released after a short time, through the public script interface.
- [x] Decide whether `test_partial_parallel_launch_failure_stops_started_consultation` shares this cause. Either the fix makes it pass, or it gets its own ticket.

## Comments

### 2026-09-25 — diagnosis so far

- **The suite failure has a different cause: a test harness defect, not a product lock.** A replay of `test_partial_parallel_launch_failure_stops_started_consultation` showed the following sequence:
  - `collect` correctly reports `stop_unconfirmed` and retains the run, because the test sets `ASK_CODEX_STOP_WINDOW_S=1`.
  - `run.sh` finishes its stop verification about 3–4 s later, writes `launcher-result.json`, and exits. No process survives.
  - The test's `TemporaryDirectory` cleanup runs as soon as `collect` returns, so it races the launcher that is still settling.
- **The live lock is reproducible.** Three live consultations were run (gpt-6-sol high, trivial prompt, base `D:\tmp\ac-lock`); two of them produced `cleanup_failed`.
  - Both failing runs had a Git Bash `grep` read the run files before `collect`. The one run without it cleaned up normally. The sample is too small to say the grep matters.
  - The locked files were exactly `0/events.jsonl`, `0/prompt.md` and `0/stderr.log`, all with WinError 32. These are the worker's stdout, stdin and stderr handles from `Popen`.
  - The lock lasted about 13 s. After that, `cleanup` returned `cleaned`.
  - While the lock lasted, no process had the run directory name in its command line. `codex.exe` and `run.sh` had already exited.
  - **Reading:** some process that inherited the worker's std handles, and is not in the recorded tree, outlives the run by seconds. It may be a Codex Windows helper; this has not been verified yet. If that is right, retrying only treats the symptom, and `run.sh`'s normal-completion survivor check misses that process.

### 2026-09-25 — the holder is not a leftover from the run

- Four more live consultations, all with the grep replay. None of them locked, so the tally is now 2 of 7.
- In three of those runs, a full process snapshot was taken right after `run` returned and compared against a snapshot taken before `prepare`. No process created during the run was still alive; only the probe's own `powershell.exe` and `wmiprvse.exe` were excluded.
- **Reading:** the holder is most likely a process that was already running and opened the three files by path, not a Codex helper that inherited the handles. Windows Defender or the search indexer scanning freshly written files would fit, and would also explain why the lock is intermittent. `run.sh`'s survivor check is therefore not implicated.
- **Not proven:** that needs `handle.exe` (Sysinternals) at the moment of the lock, and it is not installed here.
- **Consequence for the fix:** a bounded retry in `remove_run` treats the actual situation, a brief external holder, rather than hiding a leak. The longest lock seen was about 13 s.

### 2026-09-25 — resolved

- **Product.** `remove_run` retries a `PermissionError` on each unlink, `rmtree` and the final `rmdir`.
  - All retries share one window: `ASK_CODEX_CLEANUP_WINDOW_S`, default 30 s, polling every 0.25 s.
  - When the window runs out, the error stands, so `collect` still reports `cleanup_failed` with `retained_location`.
  - `plan.json` is still deleted last, and is rewritten if the directory cannot be removed.
- **Tests.** Two new Windows-only tests use a child process that holds `0/events.jsonl` open.
  - A 2 s hold: `collect` succeeds and the directory is gone. This test fails on the previous `consult.py` with `cleanup_failed`.
  - A 6 s hold against a 1 s window: `collect` delivers the reply and reports `cleanup_failed`. After the holder exits, `cleanup` returns `cleaned`.
- **Existing tests.**
  - `test_cleanup_failure_preserves_delivered_reply_and_reports_location` simulates a lock that never clears. It now sets a 0.5 s window, so it stays inside its own 30 s timeout.
  - `test_partial_parallel_launch_failure_stops_started_consultation` now waits up to 60 s for `0/launcher-result.json` before teardown. That was its whole failure; it predates this ticket.
- **Results.**
  - The full harness passes: 71 of 71, including the test that used to fail.
  - One live consultation after the fix was clean: exit 0, directory removed. The lock did not occur in that run, so the live fix itself is shown only by the offline tests.
- **Open.** The holder's identity was never proven; see the Comments above. The R: `OSError` from the Evidence section was not investigated.
