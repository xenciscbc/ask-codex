# 01 — Codex child agents can write during a read-only consultation

Status: needs-triage

**What happened (2026-10-06, codex-cli 0.159.3, ask-codex 1.3.1):** with Codex's `multi_agent` feature enabled (stable, default true) and codex-feather installed (user-level `D:\codex\agents\*.toml`: analyst, executor, mech-executor, security-executor declare `sandbox_mode = "workspace-write"`; scout `read-only`), a consultation started exactly as `consult.py` starts it (`codex exec -s read-only --ephemeral …`, same preflight MCP overrides) could spawn an `executor` child that **created a file in the project**. The read-only guarantee of `ask`, `review` and `discuss` does not hold for child agents.

Probes on a throwaway repository (`D:\tmp\subagent-probe`, removed), one real Codex call each, prompt asking for an executor child that writes `probe-executor.txt`:

| Probe | Extra arguments | Child spawned | File written |
|---|---|---|---|
| 1 (through `consult.py` prepare/run/collect) | none | executor and scout yes; generic child failed (`no rollout found` — ephemeral thread) | **yes** |
| 2 (`probe-disabled.py`) | `--disable multi_agent` | yes | **yes** |
| 3 (`probe-agentsoff.py`) | `-c agents.enabled=false` | no — "no child-agent spawning tool is available" | no |

Also observed in probe 1: named children requested their codex-feather role models (executor `gpt-6.1-sol`/medium, scout `gpt-6-luna`/low), not the consultation's `-m gpt-5.6-sol`; Codex read the `feather-delegation` skill first; the `codex exec --json` event stream carries no spawn or child events (only the main agent's messages), so a consultation cannot tell from events alone that children ran. Guards: `config.toml` hash unchanged, no leftover Codex processes.

Evidence: `.scratch/subagent-boundary/evidence/` (events, final replies, argv of probes 2 and 3) and the probe scripts beside it.

Sources: Codex docs, subagents — "Subagents inherit your current sandbox policy", custom agent `sandbox_mode` overrides it, `agents.enabled` defaults to true (https://learn.chatgpt.com/docs/agent-configuration/subagents); openai/codex#45482 (exec children ignore the role's read-only and inherit the parent's workspace-write, model honoured). Probe 1 shows the other direction too: a workspace-write role under a read-only exec parent could write.

**Blocked by:** None — can start immediately. Security-sensitive: needs a security review and an approved plan before any change.

- [ ] Decide the boundary: no children in consultations (`-c agents.enabled=false`), or children limited to read-only lookups with the analysis and answer reserved for the main agent (user's preferred direction) — only if a read-only-only child can be guaranteed, which these probes did not show.
- [ ] Script change in `consult.py` with its offline oracle and stub argv checks updated; live probe proving no child can write; README known-risk entry and ADR.
