# 12: Cleanup survives a transient Windows file lock after a run ends

**What to build:** `remove_run` (`skills/ask/scripts/consult.py:142`) deletes a finished run directory with a single `shutil.rmtree` / `unlink` pass. On Windows, a handle to a run file can stay open for a short time after the run ends. When that happens, deletion fails with `PermissionError` (WinError 32). `collect` then reports `cleanup_failed`, even though the reply was delivered. Deletion should survive a lock that clears within a short, bounded time. A lock that does not clear still ends in `cleanup_failed` with `retained_location`, as it does today.

**Blocked by:** None (can start immediately).

Status: needs-triage

## Evidence

- **Live, 2026-09-25, after the v1.1.1 push.** Real consultation on Codex CLI 0.156.1, `gpt-6-sol` high, base `D:\tmp\ac-live`.
  - `collect` returned the structured reply, exit 0, then printed `{"state": "cleanup_failed", "retained_location": ...}`.
  - An immediate `cleanup` also failed, with `PermissionError: consultation operation failed`.
  - About a minute later, every run file opened with exclusive access, and no process's command line referenced the run.
  - A second `cleanup` then returned `cleaned`.
- **Suite.** `test_partial_parallel_launch_failure_stops_started_consultation` fails on `main` with the same class of error (WinError 32 on `0/events.jsonl` during test cleanup). It failed on `6efee99` and on `adb3a16` alike, so the failure predates v1.1.1. It is probably the same cause, but that has not been confirmed.
- **Also seen, 2026-09-25, cause not yet known.** `cleanup` failed with `OSError` on a run under the R: RAM disk, with a base under the scratchpad. That run was only prepared, never started. It may be a different issue.

## Acceptance

- [ ] A lock that is released within a bounded time does not fail `collect` or `cleanup`, and that time stays well inside the Bash tool's timeout.
- [ ] A lock that is not released still yields `cleanup_failed` with `retained_location`. The reply is never lost, and a later `cleanup` can finish the job.
- [ ] Deletion never goes past the run directory, and `plan.json` is still removed last.
- [ ] An offline test reproduces a lock that is released after a short time, through the public script interface.
- [ ] Decide whether `test_partial_parallel_launch_failure_stops_started_consultation` shares this cause. Either the fix makes it pass, or it gets its own ticket.
