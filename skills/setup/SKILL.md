---
name: setup
description: Create or update the ask-codex MCP policy — which Codex MCP servers an ask-codex consultation may use — by writing the user-level or project-level ask-codex config. Use when the user runs /ask-codex:setup or asks to configure which MCP servers ask-codex allows.
---

# ask-codex: MCP policy setup

ask-codex consultations disable every Codex MCP server by default, because MCP servers run outside Codex's read-only sandbox. This skill writes an **ask-codex config** that allows specific servers, or switches to **minimal-deny** mode (only `node_repl` and `cua_repl` disabled).

- User-level config: `<home>/.claude/ask-codex.json` — applies to every project.
- Project-level config: `<project directory>/.claude/ask-codex.local.json` — overrides the user config key by key; ask-codex asks the user to confirm a project config that widens the policy once per session.

Content (JSON): `{"mcp_policy": "allowlist" | "minimal-deny", "mcp_allow": ["<server>", …]}`.

## Ground rules

- Only write what the user chose, and only the file for the scope they chose. Never write the other scope's file, and never edit Codex's own `config.toml`.
- Write the file with the Write tool only. If the write fails (for example the location is read-only or not permitted), tell the user the file was not written and why, and stop — do not work around it with shell commands or another location.
- Never use `cd`; run commands in another directory with `env -C '<dir>' …`. Write paths literally in single quotes.
- The **project directory** is your current working directory. Use forward slashes.

## Procedure

1. **Home directory** (for the user-level path), in a form the file tools understand:

   ```bash
   command -v cygpath >/dev/null && cygpath -m "$HOME" || printf '%s\n' "$HOME"
   ```

2. **Servers Codex can see** (global and project Codex config):

   ```bash
   env -C '<project directory>' codex mcp list --json
   ```

   List the server names for the user. Every name must match `^[A-Za-z0-9_.-]+$`.

3. **Answers.** You need three answers: **scope** (`user` or `project`), **mode** (`allowlist` or `minimal-deny`), and, for allowlist, **which servers to allow** (may be none).
   - If the user's message already gives them (for example `Scope: user. Mode: allowlist. Allow: comfyui.`), use those and ask nothing more.
   - Otherwise ask with `AskUserQuestion`: mode and scope as single-choice questions; servers as multi-select questions of at most four options each (batch them). If `AskUserQuestion` is unavailable, ask in plain text and stop without writing anything.
   - Warn (but still allow) when an allowed name is not in the current listing. Reject names that do not match the pattern.

4. **Show the current file** for the chosen scope, if it exists (Read tool), so the user sees what changes.

5. **Write** the chosen file with the Write tool — `<home>/.claude/ask-codex.json` for user scope, `<project directory>/.claude/ask-codex.local.json` for project scope — containing exactly the chosen `mcp_policy` and `mcp_allow` (use `[]` for minimal-deny or when nothing is allowed).

6. **Report**: the file written, its content, and what a consultation will now do, using the matching statement:
   - `MCP: all servers disabled for this consultation.`
   - `MCP: allowed — <names>; all other servers disabled.`
   - `MCP: minimal-deny — only node_repl and cua_repl disabled; other servers stay usable outside the sandbox.`

   Report in the conversation language; the statements above describe the required information, not mandatory English wording. Remind the user that allowed servers run outside Codex's sandbox and may include tools that write or execute, and — for project scope — that `.claude/ask-codex.local.json` is meant to stay out of version control. Confirming a project definition does not itself authorize its use; consultations separately enforce the policy and definition-bound use authorization. An existing invalid policy file aborts consultation preflight instead of silently falling back.

7. If the same message also asks to consult Codex, continue with the `ask` skill (`/ask-codex:ask`) for that question.
