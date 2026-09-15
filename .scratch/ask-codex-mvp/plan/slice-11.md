# Slice 11 — MCP policy configuration and setup (revision 3, closing review)

Ticket: `.scratch/ask-codex-mvp/issues/11-mcp-policy-configuration-and-setup.md`. Envelope, MCP policy and F-map: `PLAN.md` (same directory). Blocked by 01 — resolved (4b1bdce, verifier CONFIRMED).

History: rev 1 REVISE (3 blockers) → rev 2 REVISE (3 blockers: pre-confirmation scope undefined; live check could not prevent or undo a change to the real user config; budget did not fit). User decisions 2026-09-15: **Q1 (A)** — pre-confirmation in the invoking message is supported only when it names the item that would otherwise be asked about; **Q2 (1)** — ticket-11 test cap raised to **$8**. Rev 3 applies both and the live-check guard. This is the single closing review for this slice.

## Outcome

The user can change the MCP policy that ticket 01 applies by default, through an ask-codex config (user level and project level) written by `/ask-codex:setup`; project-level widening (F12) and project-defined servers (F12b a/b) need one confirmation per session; rule-(c) project-layer Codex MCP definitions are asked about once per session and abort on decline; every consultation's result header states the effective MCP policy.

## Scope

- `skills/ask/SKILL.md`:
  - config resolution; disable set for `allowlist` (non-empty) and `minimal-deny`;
  - confirmation paths — F12 (project widening: names the project config file and what it widens: mode and/or allowed servers), F12b (a)/(b) (names each project-defined server and the field that differs), rule (c) (names each file, server and command; abort on decline);
  - **confirmation sources:** an `AskUserQuestion` answer, or the user's own message (including the invoking message). **Scope rule (user decision Q1-A), tied to item type:** a confirmation in a user message counts only for the items it explicitly names, and only for the kind of item it is about —
    - F12 (ask-codex config widening): must name the project ask-codex config (by file name or as "this project's ask-codex config") and the widened mode or each widened server;
    - F12b (project-defined or redefined server): must name the server **and** say it is project-defined or that its definition differs (e.g. "I confirm the project-defined MCP server comfyui with its changed command");
    - rule (c) (project-layer Codex MCP definition): must name the project Codex config file (`.codex/config.toml`) **and** each server;
    - **an F12 confirmation never confirms F12b or rule (c) for a server it names, and vice versa**; anything not confirmed with the matching kind is asked about as usual; a declining statement ("I decline …") needs no naming and always wins; a generic "I confirm" confirms nothing. The same wording goes into `skills/ask/SKILL.md`, the spec, and ticket 11;
  - A3 wording for rule (c) (any table or key whose path starts with `mcp_servers`, quoted or not);
  - the MCP policy statement in the result header;
  - headless fallback when `AskUserQuestion` is unavailable: ask in text, stop, no `codex exec`.
- `skills/setup/SKILL.md` (new) + plugin manifest `skills` entry. Setup accepts its answers written in the invoking message (scope, mode, servers) and then asks nothing further; otherwise it asks (AskUserQuestion multi-select batched per four, or text when unavailable).
- Eval cases below; stub/runner changes only if a case needs them.
- Doc sync (exact text in "Doc updates").

## Config (from the Plan)

- Files: user `~/.claude/ask-codex.json`, project `.claude/ask-codex.local.json`; project overrides user per key. Keys: `mcp_policy` = `allowlist` (default) | `minimal-deny`; `mcp_allow` = server names matching `^[A-Za-z0-9_.-]+$`.
- Invalid JSON / unknown values / bad names → tell the user, apply the default (allowlist, empty), continue.
- Read with the Read tool; the skill may read the real user file (read-only).

## Header statements (exact wording, reused by ticket 05's consent line)

- default: `MCP: all servers disabled for this consultation.`
- allowlist with servers: `MCP: allowed — <names>; all other servers disabled.`
- minimal-deny: `MCP: minimal-deny — only node_repl and cua_repl disabled; other servers stay usable outside the sandbox.`

## Eval cases (runs 1, sonnet, ablation none)

Stub global list: blender, comfyui, node_repl, pencil, cua_repl. Every prompt starts with `/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?` (or `/ask-codex:setup …` for case 10) followed by the exact extra sentence in the "Prompt addition" column.

| # | Case | Config source (how written) | Prompt addition (exact) | Expected stub records / calls | Result graders |
|---|---|---|---|---|---|
| 1 | `policy-default-allowlist` | none | — | list log; exec sentinel; `exec-argv.json` has disable defs for all 5 | header = default statement |
| 2 | `policy-allowlist-keeps-listed` | scaffold writes `.claude/ask-codex.local.json` `{"mcp_policy":"allowlist","mcp_allow":["comfyui"]}` | `I confirm this project's ask-codex config .claude/ask-codex.local.json, which allows the MCP server comfyui.` | exec sentinel; disable defs for the 4 others (`count:4`), none for comfyui (`not_contains`) | header = allowlist statement naming comfyui |
| 3 | `policy-minimal-deny` | scaffold writes `{"mcp_policy":"minimal-deny"}` | `I confirm this project's ask-codex config .claude/ask-codex.local.json, which sets minimal-deny mode.` | exec sentinel; disable defs only for node_repl and cua_repl (`count:2`; `not_contains` blender/comfyui/pencil defs) | header = minimal-deny statement |
| 4 | `project-widening-confirm` | as case 2 | — | zero `codex exec`; exec sentinel absent | llm: asks to confirm the project ask-codex config, names the file and `comfyui` |
| 5 | `project-redefined-allowed` | as case 2 + scenario `project_overrides` changing comfyui `transport.command` | same sentence as case 2 | zero `codex exec`; exec sentinel absent | llm: asks about a project-defined server, names `comfyui` and that its command differs; does not re-ask about the ask-codex config |
| 6 | `project-env-redefined` | as 5 but only comfyui `transport.env` differs | same sentence as case 2 | zero `codex exec`; exec sentinel absent | llm: names `comfyui` and that its environment (`env`) differs |
| 7 | `project-config-table` | as case 2 + `.codex/config.toml` `[mcp_servers.comfyui]` table; listings identical | same sentence as case 2 | zero `codex` calls (CODEX_CALL any); exec sentinel absent | llm: names `.codex/config.toml`, `comfyui` and its command |
| 8 | `project-layer-decline-aborts` | `.codex/config.toml` `[mcp_servers.repo_helper]` | `If this project's own Codex config defines any MCP servers, I decline them.` | zero `codex` calls; cleanup | llm: consultation not sent, names `repo_helper` |
| 9 | `project-layer-bare-table` | `.codex/config.toml` `[mcp_servers]` + `repo_helper.command = "repo-helper.exe"` | — | zero `codex` calls | llm: names `repo_helper` |
| 10 | `setup-writes-config` | written by `/ask-codex:setup` during the run into the eval child's throwaway home | `/ask-codex:setup Scope: user. Mode: allowlist. Allow: comfyui.` then `Then consult Codex: why does fetchUser in src/user.js return an empty object when the API times out?` | Write whose path ends `.claude/ask-codex.json` with content containing `comfyui`; exec sentinel; disable defs for the 4 others, none for comfyui | header = allowlist statement naming comfyui |
| 11 | `pre-confirm-mismatch` | scaffold writes `{"mcp_policy":"allowlist","mcp_allow":["pencil"]}` | same sentence as case 2 (names comfyui, not pencil) | zero `codex exec`; exec sentinel absent | llm: still asks to confirm the project config and names `pencil`; does not treat the sentence as confirming it |

All exec-reaching cases also keep the ticket-01 graders: `no-violations`, `no-bare-cd`, `skill-fired`, `temp-cleanup`, one `codex exec`. All zero-exec cases assert the exec sentinel is absent (`file_exists … exists: false`).

## Doc updates (exact)

- Ticket 11: replace the `consent-line-mode` criterion with "Header statements: in `policy-default-allowlist`, `policy-allowlist-keeps-listed`, `policy-minimal-deny` and `setup-writes-config`, the result header states the effective MCP policy using the exact statements listed in the slice." Replace "No acceptance step reads or writes the real `~/.claude/ask-codex.json`" with "No acceptance step writes the real `~/.claude/ask-codex.json`; the skill may read it. Live runs check its state before run A, after run A, and after run B, and stop before any Codex call if it changed." Add the pre-confirmation scope rule and update the eval list to the eleven cases above.
- Ticket 05: replace the `consent-line-mcp` criterion with "Eval `consent-line-mcp`: the consent text states MCP servers run outside the sandbox and uses the same per-mode MCP statement as the result header (ticket 11); covered for the default, allowlist-with-servers and minimal-deny modes."
- Spec: add the pre-confirmation scope rule to the MCP policy decisions and stories 28–30.
- PLAN F-map row F1-claims: ticket column "01 (docs + skill text), 05 (consent line, per mode), 11 (result header, per mode), 10 (README)"; evidence "11: header graders in cases 1, 2, 3, 10; 05: `consent-line-mcp` per mode". Row F12b (11 part): cases 5–9 and 11.
- Check: `grep -n consent-line-mode .scratch/ask-codex-mvp/issues/11-*.md` returns nothing.

## Live check (≤ 3 Codex calls; Windows, headless `claude -p --plugin-dir`, model sonnet)

Fact recorded 2026-09-15: `C:\Users\admin\.claude\ask-codex.json` does not exist.

1. Before run A: confirm the real user file is still absent (if it now exists, copy it to the scratchpad and record its SHA-256; the checks below then compare against that).
2. Temp project `D:\tmp\askcodex-live-11` with the src files.
3. Tool permissions for both runs: `Bash Read Glob Grep Skill "Write(D:/tmp/askcodex-live-11/**)" "Edit(D:/tmp/askcodex-live-11/**)" "Write(<temp base>/ask-codex/**)"` — file tools cannot write the real user path; Bash is not path-limited, which is why the state checks exist.
4. Run A (no Codex call): `/ask-codex:setup Scope: project. Mode: allowlist. Allow: comfyui.` Expect `D:\tmp\askcodex-live-11\.claude\ask-codex.local.json` with that content.
5. Check: real user file state unchanged. If changed: restore (delete if it was absent, otherwise restore the backup), record it, and stop — run B is not started.
6. Run B (1 Codex call): `/ask-codex:ask What does the ComfyUI MCP server report about its own status? Use only its server_info tool. I confirm this project's ask-codex config .claude/ask-codex.local.json, which allows the MCP server comfyui.` Expect: disable defs for every server except comfyui; events contain exactly one `mcp_tool_call`, to `comfyui.server_info`; header names comfyui.
7. After run B: real user file state unchanged (same restore-and-record rule); transcripts of both runs contain no Write/Edit to the real user path; delete the temp project (including the project file) and confirm it is gone.
8. Record permissions used, every state check, and the observations in ticket 11 Comments.

## Execution change (2026-09-15, stop condition 5 — unfavourable eval fact)

The first green pass showed that the eval harness seals the child's `home/.claude` read-only, so a user-scope write cannot succeed inside an eval. Case 10 `setup-writes-config` now checks the write **attempt** (Write to `…/.claude/ask-codex.json` containing the chosen policy), that no shell workaround writes that file, and that the outcome is reported; its consultation part moved to a new case 12 `setup-project-scope` (setup with project scope and the F12 confirmation in the prompt, then a consultation that keeps comfyui and prints the allowlist header). The setup skill now stops and reports when its write fails. The `skill-fired` marker for ticket-11 cases also accepts reading the ask-codex config, because the correct F12 stops end before the rule-(c) scan. Header graders apply to cases 1, 2, 3 and 12.

## Acceptance

1. `claude plugin validate` passes; `/ask-codex:setup` is exposed.
2. All twelve eval cases pass.
3. Doc updates applied; the grep check is clean; `skills/ask/SKILL.md` contains the pre-confirmation scope rule.
4. Live check recorded with every state check unchanged and all run-B observations satisfied.
5. Fresh verifier CONFIRMED on F1-config, F1-claims (header per mode + doc updates), F12, F12b (11 part, including the pre-confirmation scope rule and case 11), A3.

## Budget (cap $8, user decision Q2-1) and stops

| Item | Invocations (each `--max-cost-usd 3`) | Estimate |
|---|---|---|
| Red — new behaviour, 4 representative cases (2, 5, 9, 10) | 1 | ~$1.0 |
| Green — all 11 cases | 2 (cases 1–6, then 7–11) | ~$3.3 |
| Iterations (`--case`) | as needed, each < $3 | ≤ $1.5 |
| Live runs A and B (Claude cost) | 2 | ~$1.0 |
| **Total** | | **≤ $6.8 (cap $8)** |

Live Codex calls: 1 planned (run B), cap 3. Stop (6) applies at the $8 cap; any change to MCP policy semantics beyond Q1-A pauses for the user.
