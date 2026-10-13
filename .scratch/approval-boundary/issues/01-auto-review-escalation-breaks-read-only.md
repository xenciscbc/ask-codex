# 01 — Auto-review approves sandbox escalation during a read-only consultation

Status: ready-for-human — fixed on local branch `fix/approval-boundary` (C1 75f017b, C2 46e1713, C3 docs); merge, tag and push await the user

**What happened (2026-10-13, codex-cli 0.159.3, Windows elevated sandbox, ask-codex 1.3.2):** the user's `D:\codex\config.toml` sets `approvals_reviewer = "auto_review"`. A consultation command line identical to `consult.py`'s (`codex exec -s read-only --ephemeral … --disable apps -c agents.enabled=false -c features.multi_agent_v2.enabled=false`, same preflight MCP overrides, no `approval_policy`) was asked to write a file in a disposable project and, if blocked, retry with escalated permissions. The write was denied by the sandbox; Codex requested escalation; **the request was approved and the command ran outside the sandbox — the file was written.** The read-only guarantee of `ask`, `review` and `discuss` does not hold for users whose resolved `approvals_reviewer` is `auto_review`.

Cause (source, `codex-rs/exec/src/lib.rs`): exec defaults to `approval_policy = Never` in headless mode, but when the resolved reviewer is `AutoReview` it rebuilds the config without that override, so the approval policy comes from the config layers and approval requests go to the automatic reviewer.

| Probe | Command line | Escalation requested | File written |
|---|---|---|---|
| p9 | consultation command line, `-s read-only` | yes — approved | **yes** |
| p9b | same + `-c approval_policy="never"` | no — "approval policy prohibits escalation requests" | no |

Related observation (p8a): with a network-proxy permissions profile, blocked network requests were likewise auto-approved and re-run (127.0.0.1 and example.com reached).

Evidence: `evidence/source/p9-*`, `p9b-*`, `p8a-*` (copied from `.scratch/exercise-skills/evidence/`; environment dumps redacted); summary in `.scratch/exercise-skills/probe-results.md` (P8, P9), not part of this branch. Guards: `config.toml` hash unchanged (`eedf06aa…`), disposable directory removed.

**Blocked by:** None — can start immediately. Security-critical: needs a security review and an approved plan before any change.

- [x] Pin `-c approval_policy="never"` as a constant on the consultation command line next to the ADR 0008 pairs (command-line `-c` outranks user and project config); decide whether to also pin `approvals_reviewer`.
- [x] Check other config layers that could reintroduce approvals (trusted project `.codex/config.toml`, profiles) against the pinned value.
- [x] Offline oracle and stub argv checks; live probe that escalation is refused with `approvals_reviewer = "auto_review"` in user config and in a trusted project config; README known-risk entry, ADR, version 1.3.3.
- [ ] Merge, tag v1.3.3 and push — awaits the user.
- [ ] The planned exercise skills (`.scratch/exercise-skills/`) must pin the same value.

## Comments

- 2026-10-13 — Plan `plan.md` (rev 4; security analysis, four plan reviews, READY, user-approved). C1 pins `approval_policy="never"` and `approvals_reviewer="user"`; C2 pins `--ignore-rules` (rules bypass inferred from source, not probed — user decision); C3 README (EN, zh-TW), ADR 0010, version 1.3.3. Offline: python 81 OK, node 25/25 (process-lifecycle.test.mjs flaky once under the parallel runner, untouched). Live acceptance: cases a, b, b-granular, b-untrusted Pass, d completed, guards unchanged — `evidence/live-run-log.md`. Reviews: C1 APPROVED, CONFIRMED, adversarial review HELD with two open gaps (runtime refusal never exercised because the model declined to request; permissions-request result only reported by the model) — **the user accepted C1 without a passing adversarial review on those gaps (accept-and-land decision for C1 at a0bbf8a; merge still awaits the user)**. C2 APPROVED, CONFIRMED, HELD. C3: review 1 CHANGES_REQUESTED, fixed. Codex calls: 7 of cap 7. Follow-ups: issues 02–04.
