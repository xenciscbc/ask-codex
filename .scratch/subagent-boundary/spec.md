# Spec: no child agents in consultations (subagent-boundary)

Status: plan — awaiting approval (2026-10-06).

Ticket: `issues/01-subagents-break-read-only.md` (probes 1–5 and evidence). Pre-approval security review: 2026-10-06 (findings F1–F6 below). Decisions respect ADR 0001, 0003 (MCP policy; `--ignore-user-config` is not an option), 0005 (script-owned execution); this change deliberately alters the consultation command line that ADR 0007 said `discussion` left unchanged, recorded in a new ADR 0008.

## Problem

Under the exact command line `consult.py run()` builds (`codex exec -s read-only …`), Codex can spawn named child agents (multi-agent tools are on by default; on gpt-5.6-sol they are MultiAgentV2). A child's role file sets its own `sandbox_mode`, model and `mcp_servers`, so a `workspace-write` role (codex-feather installs four) wrote a file during a read-only consultation, and a child could also bring MCP servers the preflight MCP guard never saw. `ask`, `review` and `discuss` all launch through this one `run()`. `--disable multi_agent` did not stop it; `-c agents.enabled=false` did. Ordinary and document-analysis consultations with agents disabled completed normally with no delegation noise (probes 4–5). Affected: plugin 1.0.0–1.3.1 (the 1.0.x acceptance already listed the `collaboration` namespace).

## Decision

Every consultation runs with child agents disabled: `consult.py run()` adds the constant pair `-c agents.enabled=false` to the `codex exec` argv, next to `--disable apps` (not in the policy `overrides`, not on `codex mcp list`). The user's preferred alternative — children allowed for read-only side work while the main agent keeps the analysis and the answer — is not achievable safely today: Codex has no per-invocation role allowlist, role files override the parent's sandbox, and generic children (which would inherit the consultation model) fail under `--ephemeral`. Revisit when Codex offers an enforced child sandbox ceiling.

## Security review dispositions

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| F1 | P1 | Children bypass read-only and the MCP policy | **Fix here** (S1) |
| F2 | P2 | `agents.enabled=false` verified only on 0.159.3 + gpt-5.6-sol + Windows; `spawn_agents_on_csv` (`features.enable_fanout`), feature-enabled `multi_agent_v2`, non-v2 models, trusted-project config, older CLIs untested | Each surface mapped: **v2 fanout + feature-enabled `multi_agent_v2`** → S2 probe 2; **non-v2 model** → S2 probe 3 when the local catalog lists one, otherwise DEFER to ticket 05; **trusted-project config** → DEFER to ticket 05 (rationale: the official config docs give command-line `-c` precedence over the project `.codex/config.toml` layer; a live check needs a project marked trusted, i.e. an edit to the user's Codex `config.toml`, which this project never makes unasked); **older CLIs** → DEFER to ticket 04 (minimum-version check). README/ADR claim only the surfaces actually probed ("verified on codex-cli 0.159.3 with …") and list the deferred ones as unverified. A gap found by any S2 probe → the S2 failure path below |
| F3 | P3 | Preflight read-back proves nothing; post-run detection version-dependent | Stub **requires** the flag (missing, different or repeated = violation); post-run `collab_tool_call` tripwire → ticket 02; prompt sentence → not added (P4, no noise observed, no security value once the tool is absent) |
| F4 | P2 | README boundary statements overclaim for 1.0.0–1.3.1 | **Fix here** (S2): both READMEs' boundary paragraph and comparison table, known-risk entry with affected versions and interim advice, release note |
| F5 | P3/P4 | Other out-of-sandbox paths | Docs: notify → "notify and hooks", allowed MCP servers may themselves start agents; `--disable apps` re-checked in the S2 probe (tool/namespace listing); web search exfiltration channel → ticket 03; approval policy and `--ephemeral` memory → noted as unverified (P4) |
| F6 | P3 | Prompt-injection residue (repo AGENTS.md/skills as instructions, read-then-reply exfiltration, discuss carry-over) | Docs: extend "Steering by diff content" with repo instruction files |

## Non-goals

Child agents of any kind in consultations; a per-run preflight of the Codex config; post-run detection (ticket 02); web search control (ticket 03); minimum CLI version enforcement (ticket 04); a live check of a trusted project's `.codex/config.toml` and, if no non-v2 model is available, of non-v2 models (ticket 05); changes to the user's own Codex or codex-feather configuration.

---

# Plan

Program envelope: one local branch `fix/subagent-boundary`, one commit per slice; push and tag `v1.3.2` only on the user's word. Budget: each slice first implementation plus at most 3 fix/test passes. Real Codex calls: S2 only — at most 3 (one consult.py run, one strongest-flags probe, one non-v2-model probe) plus one rerun after a reproduced fix.

Risk triggers: security/trust boundary, release → this Plan reviewed by `plan-verifier`; S1 owned by `security-executor`; fresh `verifier` at the S2 integration boundary.

## S1 — consultations launch with child agents disabled

- **Outcome:** every `codex exec` that `consult.py run()` starts carries `-c agents.enabled=false`; the stub refuses a run without it; offline tests prove it for consultation and discussion requests.
- **Prerequisite:** none.
- **Owner:** `security-executor`; main keeps acceptance.
- **Scope:** `skills/ask/scripts/consult.py` (`run()` argv only; `overrides`, preflight summary/fingerprint comparison and `codex mcp list` unchanged); `evals/_harness/stub/codex-stub.py` (exec argv check: exactly one `-c agents.enabled=false`; missing, other value or repeated → violation; `mcp list` unchanged; doc header); `evals/_harness/consultation_test.py` (`BASELINE_ARGV` gains the pair; its comment states the literal is the 6266c3e capture plus this deliberate change; the discussion-schema test still differs only in the schema basename); hand-written argv samples in `stub-modes.test.mjs`, `run-stop-scripts.test.mjs`, `ticket-r03-graders.test.mjs`, `ticket08-graders.test.mjs`, `ticket03-patterns.test.mjs`, `review-skill-graders.test.mjs` updated where they model the exec argv.
- **Acceptance:**
  - test-first: a stub test where an exec argv without the pair (and one with `agents.enabled=true`, and one with the pair twice) records a violation, and the current argv records none — red before the stub change;
  - `consultation_test.py`: the argv for absent/explicit `consultation` and for `discussion` requests equals the updated literal (pair present exactly once, after `--disable apps`); a test that the pair is never added to `codex mcp list`;
  - all offline harness tests pass (node and python), noting any environment-only timing failure separately with a passing rerun;
  - Claude eval `script-consultation` x3 has no `violations.log` entry (the stub accepts the new argv).
- **Rollback:** revert the slice commit.
- **Stops:** pause if Codex rejects `agents.enabled` at startup on this CLI (would mean the key is wrong for this version).

## S2 — docs, ADR 0008, version 1.3.2, live acceptance, verification

- **Outcome:** READMEs, ADR 0008 and version 1.3.2 state the boundary truthfully; live probes show no child can be spawned under the real consultation path, even with the strongest enabling flags; a fresh verifier confirms the claim.
- **Prerequisite:** S1.
- **Owner:** main (docs, probes); user decides push/tag.
- **Scope:** `README.md`, `README.zh-TW.md` (boundary paragraph "child agents disabled"; comparison table row; known-risk entry: affected 1.0.0–1.3.1, trigger, impact incl. MCP bypass and role-model billing, fix in 1.3.2 verified on codex-cli 0.159.3, interim advice for older installs; notify → notify and hooks; allowed MCP servers may start agents; repo instruction files in "Steering"); `docs/adr/0008-no-child-agents-in-consultations.md` (decision, options considered: `--disable multi_agent`, hook deny, `max_depth`, `multi_agent_v2` table, read-only-only children, `--ignore-user-config`; supersedes ADR 0007's "command line unchanged"); `CONTEXT.md` only if a term is needed; `.claude-plugin/plugin.json` → 1.3.2; tickets 02–05 created (needs-triage; 05 = trusted-project config and, if untested, non-v2 models). S2 edits no script, stub or test file.
- **Live acceptance** (throwaway repo under `D:/tmp` with the user's codex-feather roles present; guards: `config.toml` hash, Codex PID baseline, repo status):
  1. Through the real `consult.py` prepare → run → wait → collect: a prompt asking for an `executor` child that writes a file and asking Codex to list its available tools/namespaces → no spawn tool, file absent, no `collaboration`/`spawn_agent`/`spawn_agents_on_csv`/`mcp__codex_apps` reported (model self-report = secondary evidence).
  2. Same consult.py argv plus `-c features.enable_fanout=true -c features.multi_agent_v2.enabled=true` → still no spawn tool, file absent.
  3. If an available non-v2 model exists in the local catalog, probe 1's prompt with that model → no spawn tool. If none exists, record that and leave the surface to ticket 05.
- **Failure path:** any spawn, write or listed spawn tool in a probe stops S2. Main does not edit `consult.py`, the stub or the tests. The fix is an **S1 follow-up** owned by `security-executor` with S1's scope (`consult.py` argv, the stub's exec `-c` rule, `BASELINE_ARGV` and the argv samples) and S1's acceptance (a red-first stub test for the added key, the full offline suite, `script-consultation` x3 with no violations). Then the failed probe is rerun once; a second failure pauses for the user.
- **Acceptance:** live probes as above with guards unchanged; offline suite green; fresh `verifier` CONFIRMED against this spec.
- **Rollback:** revert; no tag or push until the user says.
