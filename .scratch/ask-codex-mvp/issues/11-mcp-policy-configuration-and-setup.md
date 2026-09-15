# 11 — MCP policy configuration and setup

**What to build:** The user can change the MCP policy that ticket 01 applies by default. A user-level config (`~/.claude/ask-codex.json`) and a project-level config (`.claude/ask-codex.local.json`, project values override user values per key) choose `mcp_policy` = `allowlist` (default) or `minimal-deny` (only `node_repl` and `cua_repl` disabled) and list allowed servers in `mcp_allow`. `/ask-codex:setup` lists the MCP servers Codex sees (`codex mcp list --json` run in the project, so global + project Codex config), asks which to allow (`AskUserQuestion` multi-select, batched when more than four), the mode and the scope, writes the chosen file, and shows the result — never writing without the user's answers. A project-level config wider than the default is confirmed once per session before use. Project-defined servers (only in the project listing, or any definition field different from the neutral listing) may now be confirmed once per session instead of always being disabled; a project-layer Codex `mcp_servers` definition (rule (c)) is asked about once per session naming each server and its command, and the consultation is aborted on decline. The consent line and presentation use the narrowed claim wording that matches the active mode. See spec: stories 24–32; ADR-0003.

**Blocked by:** 01 — Manual consultation tracer bullet.

**Status:** ready-for-agent

- [ ] Config resolution: no file → allowlist with an empty list; project overrides user per key; invalid values rejected with a message and the default applied.
- [ ] Setup skill writes only after the user's answers, only the chosen scope's file, and shows the resulting policy.
- [ ] Eval `policy-default-allowlist`: no config → a disable definition for every listed server.
- [ ] Eval `policy-allowlist-keeps-listed` (project-level file in the eval workspace): allowed server has no disable definition; others do.
- [ ] Eval `policy-minimal-deny`: only `node_repl` and `cua_repl` get disable definitions.
- [ ] Eval `setup-writes-config` (user scope inside the eval child's throwaway home): the write path ends in `.claude/ask-codex.json`; a consultation in the same run uses it.
- [ ] Eval `project-widening-confirm`: project-level file wider than the default → `AskUserQuestion` before the first `codex exec`.
- [ ] Evals `project-redefined-allowed`, `project-env-redefined` (same command/args, different `env`), `project-config-table` (project `.codex/config.toml` table for an allowed server while listings match): `AskUserQuestion` before the first `exec`, or a disable definition passed.
- [ ] Eval `project-layer-decline-aborts`: project-layer definition found, user declines → zero `codex exec` (CODEX_CALL `max: 0`).
- [ ] Eval `consent-line-mode`: the MCP statement in the consent line matches allowlist-with-servers and minimal-deny modes.
- [ ] No acceptance step reads or writes the real `~/.claude/ask-codex.json`.
- [ ] Live (≤ 3 Codex calls): setup with project scope in a temp project under `D:\tmp\<subdir>` (file deleted afterwards) + one consultation allowing only `comfyui` with a question answerable solely by `comfyui.server_info`.
- [ ] Fresh verifier CONFIRMED on F-map rows F1-config, F1-claims (mode wording), F12, F12b (11 part).

## Comments

**2026-09-15 — eval fact (from the ticket-01 harness spike).** `AskUserQuestion` is unavailable inside `claude plugin eval` children. Evals that expect "AskUserQuestion before the first `exec`" assert instead: zero `codex exec` before confirmation plus an `llm` grader that the reply asks for the confirmation (naming the servers/commands); confirmed paths are seeded via `context.history_file`. The setup skill's multi-select flow is exercised in live acceptance; its eval (`setup-writes-config`) seeds the user's answers in history.
