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

## Comments

**2026-09-15 — moved from ticket 03.** The interactive override-scope question (`AskUserQuestion`: "this consultation only" vs "rest of the session") cannot run in evals (no `AskUserQuestion` in eval children). Live acceptance here must include one consultation that names a model different from the session setting and shows that question, and one later consultation that confirms a session-scoped choice persists.

**2026-09-15 — moved from ticket 07.** Live acceptance here must cover what evals could not: (1) the interactive stall question via `AskUserQuestion` (options "wait another T minutes" / "stop this consultation", elapsed time, last event and age, recommendation by the T/2 rule), including choosing "wait" at least once; (2) F8 — after "stop", no Codex process remains (the whole process chain ends); (3) the stop report's wording, which passed an eval judge only 2–1 (and offered to "retry" as a new consultation). Also watch `temp-cleanup` (one skipped cleanup was seen in ticket-07 evals and not reproduced after the fix).

**2026-09-16 — execution mode (user decision).** The automated scenarios run headless by Claude (real Codex CLI, ≤ 16 calls in total, probe projects under `D:\tmp\<subdir>`, deleted afterwards). The three scenarios that need a person answering `AskUserQuestion` — the proactive consent prompt's three options, the override-scope question (this consultation / rest of session), and the stall question answered with "wait" at least once — are written up as step-by-step instructions for the user to perform in an interactive session; Claude then reads that session's transcript and records the outcome. Ticket 05 is paused, so the fix-loop scenario's outcome is recorded as observed (it may not propose reliably).

**2026-09-16 — slice-09 readiness: READY on revision 3.** Round 1 REVISE (5 blockers) → revision 2: the guarded files are named (`C:\Users\admin\.claude\ask-codex.json`, `D:\codex\config.toml`), backed up to `D:\tmp\askcodex-live-09-backup\` and hash-checked before and after every run with restore-and-stop, plus a Rollback section; slice-local stops with the sandbox/namespace probe A2 running first; A2 records Codex's own tool namespaces and fails if any of the six servers or `mcp__codex_apps` appears; the run prompts print each `events.jsonl` `mcp_tool_call` line and each `last-message.json` before cleanup, checked against the schema by `live-09-check.mjs`; an F8 process baseline via `Get-CimInstance Win32_Process`, a forced-stop probe A8b, and a narrowing fallback if no scenario reaches a stop. Round 2 REVISE (2 blockers), both FIX → revision 3: the F8 post-stop snapshot must be taken **inside the stopping session while it is still running** (headless: 5 s after `TaskStop`, before the final reply; I3: by the user via `!` before quitting), because a snapshot after `claude -p` exits could be cleaned up by the session's own exit; the interactive guide drops `tasklist` for a baseline handoff plus the in-session snapshot; A8b must use A2's exact command line (`-s read-only`, `--ephemeral`, `--disable apps`, one disable definition per listed server); stop 3 now names every default-policy scenario (A1, A2, A4, A7, A8, A8b, A9). Closing review: READY. Budget: ≈ 14 Codex calls of the 16 allowed (5 of 25 used program-wide). Entry gate: ticket 08's outcome verifier CONFIRMED.
