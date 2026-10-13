# 14 — `prepare` follows a pre-existing junction at `<base>\ask-codex`

Status: needs-triage

**What happened (2026-10-13, found while verifying the UI exercise's C1):** `consult.py prepare` creates the run directory with `mkdir(parents=True, exist_ok=True)` on `<base>\ask-codex` and `tempfile.mkdtemp` under it. If `<base>\ask-codex` already exists as a junction (for example planted in `%TEMP%`, the default scratch base), it is followed: the run directory and its `plan.json` — which holds the full prepared prompt — are written wherever the junction points, including inside the consulted project or another location the planting process can read. `plan_at` resolves the junction too, so later operations work on the redirected directory. Affects `ask`, `review` and `discuss` in every released version with script-owned execution (ADR 0005).

The UI exercise's own run directories are not affected: C1 (`skills/ask/scripts/target.py`, df107d5) creates them through verified handles and refuses a link at `<base>\ask-codex` (`_new_run_directory`, `_verify_run_directory`).

**Blocked by:** None. Security-critical (where prompt content is written; a trust boundary between the scratch base and other processes): needs a security analysis and an approved plan before any change, and must keep the consultation command line unchanged.

- [ ] `prepare` refuses when `<base>` or `<base>\ask-codex` resolves through a link/junction to somewhere other than itself, or creates the run directory through verified handles as C1 does; the decision is documented.
- [ ] The run directory is never inside the consulted project (resolved final path check).
- [ ] Offline tests with a junction at `<base>\ask-codex` pointing into the project and elsewhere; existing consultation tests pass; `BASELINE_ARGV` unchanged.

## Comments
