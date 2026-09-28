# 13: A run directory on a volume without final-path support fails every step after prepare

**What to build:** `plan_at` (`skills/ask/scripts/consult.py:134`) resolves the run directory with `Path.resolve(strict=True)`. On Windows that asks the volume for the file's final path (`GetFinalPathNameByHandle`). This machine's `R:` RAM disk does not support that call, so Python raises a bare `OSError(22)` (WinError 1, "Incorrect function"). `run`, `wait`, `collect`, `stop` and `cleanup` then all report `OSError: consultation operation failed`. `prepare` still works, because it resolves the base without `strict`. The interactive Claude scratchpad lives on `R:`, so on this machine every interactive consultation fails.

**Blocked by:** None (can start immediately).

Status: resolved — plan_at resolves non-strictly, like prepare (2026-09-28)

## Evidence

- **Real use, 2026-09-28, plugin 1.1.2.** Session in `cbc-go-web-seed`, base `R:\Temp\claude\…\scratchpad\codex`. `prepare` returned `prepared`. `run`, `wait` and `collect` each returned `OSError: consultation operation failed`. The run directory held only `plan.json`: no `started` and no `execution-error.json`. So the failure happened inside `plan_at`, before any Codex process started, and nothing was billed.
- **Reproduced.** On Python 3.11.9, `Path('R:/Temp').resolve(strict=True)` raises `OSError(22, …)`, and `Path('R:/Temp').resolve()` returns `R:\Temp`. `D:/tmp` resolves either way.
- The `OSError` on `R:` noted in ticket 12's Evidence was this same defect.
- The same user's first attempt, on 1.1.0, failed at preflight with `Codex preflight command failed (exit 1)`. That is the plugin MCP override rejection fixed in 1.1.1. It is not part of this ticket, and it was inferred, not reproduced.

## Acceptance

- [x] With the run base on a volume whose final-path lookup fails, `prepare`, `wait`, `run` and `collect` succeed, and the run directory is removed afterwards.
- [x] The ownership check is unchanged: `plan.json` must name the same directory that `prepare` recorded (also resolved non-strictly), and an arbitrary directory is still refused.
- [x] An offline test reproduces the failure through the public script interface. It simulates the volume by making `ntpath._getfinalpathname` raise WinError 1 under the run base. The test fails on 1.1.2 and passes with the fix.
- [x] One real harmless consultation with the base on `R:` succeeds end to end.

## Comments

### 2026-09-28 — fix

- **Why non-strict is enough.** `prepare` already writes the non-strictly resolved directory into `plan.json`, and `plan_at` compares against that. A missing directory still fails, because `plan.json` cannot be read. Symlinks are resolved wherever the volume allows it, as before.
- **Not changed.** `validate` still resolves the project with `strict=True`. A project on such a volume fails anyway, because `codex exec -C` there fails with "os error 1".
- **Suite.** 72/72 (71 before plus the new test).

### 2026-09-28 — live check

- One real consultation, run from the repo's scripts: Codex CLI, `gpt-6-sol` medium, a trivial prompt, the project an empty `D:\tmp\ac-live13`, and the base the session scratchpad on `R:`.
- `prepare` returned `prepared`. `wait --seconds 0` returned `prepared`. `run` returned `finished` after 21 s.
- `collect` returned `completed` with a structured reply and exited 0. The run directory was removed.

### 2026-09-28 — verification

- A fresh verifier returned CONFIRMED. It reproduced the failure on `R:`, ran the new test red and then green, and ran the suite at 72/72.
- It also probed ownership through the CLI. Nonexistent, arbitrary, forged and non-`ask-codex` directories are all refused. Slash, trailing-separator, `.`/`..` and relative spellings of an owned directory all resolve to that directory. On `D:`, strict and non-strict resolves give identical strings.
- **Deferred (P4).** On a volume without final-path support, a spelling of the run directory in different letter case is refused, because the case cannot be canonicalized. That refusal fails closed, and the directory `prepare` returns always works. No change.
