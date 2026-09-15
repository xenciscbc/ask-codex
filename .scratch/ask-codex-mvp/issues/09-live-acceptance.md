# 09 — Live acceptance

**What to build:** The tier-2, opt-in verification: in a real Claude Code session with the real Codex CLI, walk through every acceptance scenario and record the outcome, the Codex CLI version, and any behaviour that differs from the spec. This confirms what the offline evals cannot — real enforcement of the shell sandbox (writes denied, network blocked) and of the MCP policy, real schema-constrained replies, real consent prompts, and real timing. Prior art: `codex-feather` keeps live runs behind an explicit opt-in. See spec: Testing Decisions, Tier 2.

**Blocked by:** 02 — Consultation types and packaging; 03 — Model aliases and effort rules; 04 — Failure handling; 05 — Proactive consultation and consent; 06 — Follow-up consultation; 07 — Timeout monitoring; 08 — Parallel consultation; 11 — MCP policy configuration and setup.

**Status:** ready-for-agent

Live probe directories live under `D:\tmp\<subdir>` and are deleted afterwards. Budget: ≤ 16 Codex calls.

- [ ] Manual consultation with a question: shell writes denied and shell network blocked with the exact flags (F2), disabled MCP servers absent from Codex's namespaces, structured claims returned, dispositions presented.
- [ ] Manual consultation without a question: question inferred from context.
- [ ] Parallel `astra` + `sol`: efforts `medium` / `high`, grouped presentation.
- [ ] Simulated fix loop: consent prompt appears; all three options behave as specified.
- [ ] Ambiguous alias `5.6`: candidates offered.
- [ ] Wrong model name: no retry, no fabricated opinion.
- [ ] Follow-up consultation: only carried claims are verified; no resume.
- [ ] Timeout with a short override: auto-wait while active, prompt when stalled.
- [ ] A project path containing spaces works (F9).
- [ ] After "stop", no Codex process remains (F8).
- [ ] MCP policy: default (all disabled), an allowed lookup server usable, minimal-deny mode, and a project-layer definition prompt with decline → abort.
- [ ] Results, the Codex CLI version (`codex --version`, F10), and any deviations (plus any cases moved from tier 1 to tier 2) are recorded in the ticket comments for the README.
