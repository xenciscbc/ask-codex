# 09 — Live acceptance

**What to build:** The tier-2, opt-in verification: in a real Claude Code session with the real Codex CLI, walk through every acceptance scenario and record the outcome, the Codex CLI version, and any behaviour that differs from the spec. This confirms what the offline evals cannot — real read-only enforcement, real schema-constrained replies, real consent prompts, and real timing. Prior art: `codex-feather` keeps live runs behind an explicit opt-in. See spec: Testing Decisions, Tier 2.

**Blocked by:** 02 — Consultation types and packaging; 03 — Model aliases and effort rules; 04 — Failure handling; 05 — Proactive consultation and consent; 06 — Follow-up consultation; 07 — Timeout monitoring; 08 — Parallel consultation.

**Status:** ready-for-agent

- [ ] Manual consultation with a question: read-only confirmed (write attempt denied), structured claims returned, dispositions presented.
- [ ] Manual consultation without a question: question inferred from context.
- [ ] Parallel `astra` + `sol`: efforts `medium` / `high`, grouped presentation.
- [ ] Simulated fix loop: consent prompt appears; all three options behave as specified.
- [ ] Ambiguous alias `5.6`: candidates offered.
- [ ] Wrong model name: no retry, no fabricated opinion.
- [ ] Follow-up consultation: only carried claims are verified; no resume.
- [ ] Timeout with a short override: auto-wait while active, prompt when stalled.
- [ ] Results, the Codex CLI version, and any deviations (plus any cases moved from tier 1 to tier 2) are recorded in the ticket comments for the README.
