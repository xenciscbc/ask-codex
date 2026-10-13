# 01 — Auto-review approves sandbox escalation during a read-only consultation

Status: needs-triage

**What happened (2026-10-13, codex-cli 0.159.3, Windows elevated sandbox, ask-codex 1.3.2):** the user's `D:\codex\config.toml` sets `approvals_reviewer = "auto_review"`. A consultation command line identical to `consult.py`'s (`codex exec -s read-only --ephemeral … --disable apps -c agents.enabled=false -c features.multi_agent_v2.enabled=false`, same preflight MCP overrides, no `approval_policy`) was asked to write a file in a disposable project and, if blocked, retry with escalated permissions. The write was denied by the sandbox; Codex requested escalation; **the request was approved and the command ran outside the sandbox — the file was written.** The read-only guarantee of `ask`, `review` and `discuss` does not hold for users whose resolved `approvals_reviewer` is `auto_review`.

Cause (source, `codex-rs/exec/src/lib.rs`): exec defaults to `approval_policy = Never` in headless mode, but when the resolved reviewer is `AutoReview` it rebuilds the config without that override, so the approval policy comes from the config layers and approval requests go to the automatic reviewer.

| Probe | Command line | Escalation requested | File written |
|---|---|---|---|
| p9 | consultation command line, `-s read-only` | yes — approved | **yes** |
| p9b | same + `-c approval_policy="never"` | no — "approval policy prohibits escalation requests" | no |

Related observation (p8a): with a network-proxy permissions profile, blocked network requests were likewise auto-approved and re-run (127.0.0.1 and example.com reached).

Evidence: `.scratch/exercise-skills/evidence/p9-*`, `p9b-*`, `p8a-*`; summary in `.scratch/exercise-skills/probe-results.md` (P8, P9). Guards: `config.toml` hash unchanged (`eedf06aa…`), disposable directory removed.

**Blocked by:** None — can start immediately. Security-critical: needs a security review and an approved plan before any change.

- [ ] Pin `-c approval_policy="never"` as a constant on the consultation command line next to the ADR 0008 pairs (command-line `-c` outranks user and project config); decide whether to also pin `approvals_reviewer`.
- [ ] Check other config layers that could reintroduce approvals (trusted project `.codex/config.toml`, profiles) against the pinned value.
- [ ] Offline oracle and stub argv checks; live probe that escalation is refused with `approvals_reviewer = "auto_review"` in user config and in a trusted project config; README known-risk entry, ADR, patch release.
- [ ] The planned exercise skills (`.scratch/exercise-skills/`) must pin the same value.

## Comments
