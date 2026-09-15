# 06 — Follow-up consultation

**What to build:** When a claim is marked investigate, or Claude needs to re-check a revised Plan, Claude starts a follow-up consultation: a fresh, ephemeral Codex session (never a resumed one, per ADR-0002) that carries the prior claims and Claude's dispositions and is scope-locked to verifying them. Codex reports each carried claim as resolved, unresolved, or invalid via `followup_status`; it may add a new claim only if it is blocking, and that claim is marked `new-blocking`. Claude presents the per-claim status alongside its updated dispositions. See spec: user stories 52–54; ADR-0002.

**Blocked by:** 02 — Consultation types and packaging.

**Status:** ready-for-agent

- [ ] A dedicated English follow-up prompt template carries prior claims + dispositions and states the scope lock and the new-blocking exception.
- [ ] Follow-ups never use `resume` or `fork`; each is a new ephemeral run.
- [ ] Every carried claim comes back with a `followup_status`; non-blocking new points are not presented as new claims.
- [ ] Presentation shows each carried claim's status and Claude's updated disposition, and flags any new-blocking claim separately.
- [ ] Eval cases pass: history holds a prior consultation → the new Bash call has no `resume`, recorded stdin contains the carried claims; stub reply with a `new-blocking` claim is flagged separately by an `llm` grader.
