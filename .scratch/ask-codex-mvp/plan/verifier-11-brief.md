# Verifier brief — ticket 11 (boundary 2)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate commit given in the Agent prompt (after 4b1bdce).
Execution contract: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\slice-11.md` (rev 3 + "Execution change" section). Envelope / MCP policy / F-map: `PLAN.md` in the same directory.
Ticket: `.scratch/ask-codex-mvp/issues/11-mcp-policy-configuration-and-setup.md` (criteria + Comments with red/green/live evidence). Ticket 05 (consent-line text change), spec (confirmation-scope contract, header statements), ADR-0003.

## Exact claim to confirm or refute

Ticket 11 satisfies these F-map rows (11 parts):

- **F1-config** — ask-codex config resolution (user `~/.claude/ask-codex.json`, project `.claude/ask-codex.local.json`, project overrides per key, invalid values → default + message); `allowlist` (non-empty) and `minimal-deny` disable sets; `/ask-codex:setup` writes only the chosen scope's file after the user's answers (answers in the message or asked), stops and reports when the write fails, never works around it; no acceptance step writes the real user config (live state checks recorded).
- **F1-claims (11 part)** — the result header states the effective MCP policy with the three exact statements (skill text + graders in policy-default-allowlist, policy-allowlist-keeps-listed, policy-minimal-deny); doc updates: ticket 11 criteria, ticket 05 `consent-line-mcp` per mode, PLAN F-map F1-claims row; no `consent-line-mode` left in ticket 11.
- **F12** — a project config wider than the default needs confirmation of this project's ask-codex config before anything is sent; without it: no `codex exec`, the reply asks (project-widening-confirm).
- **F12b (11 part)** — project-defined/redefined servers that the policy would keep enabled need a typed confirmation (project-redefined-allowed, project-env-redefined); rule (c) project-layer Codex MCP definitions (any table or key whose path starts with `mcp_servers`, quoted or not — A3) need a typed confirmation, decline aborts (project-config-table, project-layer-decline-aborts, project-layer-bare-table); the **typed confirmation-scope rule** (user decision Q1-A) is in `skills/ask/SKILL.md`: a confirmation counts only for items it names and only for its own kind, a kind never covers another, generic confirmations confirm nothing, declines always win (pre-confirm-mismatch and cases 5–7 exercise it).

## Known eval-environment limits (recorded dispositions, not defects)

The eval harness seals the child's `home/.claude` read-only and denies writes under the workspace `.claude/`. So `setup-writes-config` and `setup-project-scope` verify the write **attempt** (path + content), the absence of a shell workaround and the reported outcome; reading a project config is covered by policy-allowlist-keeps-listed; the real setup → consultation path is covered by the live check (ticket 11 Comments).

## Evidence locations

- `skills/ask/SKILL.md` (Confirmations section, steps 2–5 and 10), `skills/setup/SKILL.md`, `.claude-plugin/plugin.json`.
- Cases (tag `ticket-11`) under `evals/`: policy-default-allowlist, policy-allowlist-keeps-listed, policy-minimal-deny, project-widening-confirm, project-redefined-allowed, project-env-redefined, project-config-table, project-layer-decline-aborts, project-layer-bare-table, setup-writes-config, setup-project-scope, pre-confirm-mismatch.
- Eval results: newest directories under `evals/results/` (per-case runs), and ticket 11 Comments.
- Live evidence: ticket 11 Comments (run A / run B, state checks, permissions).

## Allowed reproduction

Static reading; `claude plugin validate`; git inspection; direct stub probes in a temp dir under `D:\tmp` (delete afterwards). Do not run the real Codex CLI; do not re-run the paid eval suite.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-row findings (P0–P4) and evidence.
