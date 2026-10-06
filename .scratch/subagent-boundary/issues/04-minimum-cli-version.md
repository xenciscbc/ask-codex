# 04 — Minimum Codex CLI version for the child-agent switches

Status: needs-triage

**What to build:** `agents.enabled` and `features.multi_agent_v2.enabled` are verified on codex-cli 0.159.3 only. On older CLIs `[agents]` was a role map and the keys may be rejected (fail closed) or ignored (fail open). Decide a minimum version and how `consult.py` checks it (for example `codex --version` in preflight).

**Blocked by:** None — can start immediately.

- [ ] Minimum version stated in README; preflight refuses or warns below it; offline test with the stub.
