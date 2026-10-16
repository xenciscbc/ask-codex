---
name: setup
description: Set up ask-codex — create or update the ask-codex MCP policy (which Codex MCP servers an ask-codex consultation may use) by writing the user-level or project-level ask-codex config, or prepare this machine for /ask-codex:ui exercises (install the pinned browser server and check Chrome, node and codex-cli; Windows only). Use when the user runs /ask-codex:setup, asks to configure which MCP servers ask-codex allows, or asks to prepare a machine for ask-codex UI exercises.
---

# ask-codex: setup

This skill does two independent things:

- **MCP policy.** ask-codex consultations disable every Codex MCP server by default, because MCP servers run outside Codex's read-only sandbox. The policy part writes an **ask-codex config** that allows specific servers, or switches to **minimal-deny** mode (only `node_repl` and `cua_repl` disabled).
  - User-level config: `<home>/.claude/ask-codex.json` — applies to every project.
  - Project-level config: `<project directory>/.claude/ask-codex.local.json` — overrides the user config key by key; ask-codex asks the user to confirm a project config that widens the policy once per session.
  - Content (JSON): `{"mcp_policy": "allowlist" | "minimal-deny", "mcp_allow": ["<server>", …]}`.
- **Exercise preparation.** `/ask-codex:ui` exercises (Windows only) need Google Chrome 149 or later, node with npm, and the pinned browser server (chrome-devtools-mcp 1.10.1) installed by ask-codex itself. The exercise part installs that server and checks the dependencies. Both exercise modes (a disposable copy, or attaching to the dev servers the user already runs) need the same dependencies. An exercise never uses the MCP policy: it disables every other MCP server whatever the policy says.

## What to set up

- The user's message asks to prepare for exercises — it names `/ask-codex:ui`, UI exercises, the browser server, or Chrome or node for exercises: do **Exercise preparation** (below). Do the MCP policy as well only when the message also asks for it (a scope, a mode or servers to allow).
- Otherwise: do the MCP policy (**Procedure** below), and nothing of the exercise part.

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

## Exercise preparation

`<ask>` is the `ask` skill directory, the sibling of this skill's base directory (`<this skill's base directory>/../ask`), written as an absolute path in forward-slash form. Python 3.11+ is required: use `python` or `python3` only after checking that interpreter's version; the commands below write `python` for it. Run each command once, in the foreground, with the Bash tool's `timeout` set to 600000. Write nothing yourself: the script owns every file of this part.

1. **Install the browser server:**

   ```bash
   python '<ask>/scripts/consult.py' browser-install
   ```

   It installs chrome-devtools-mcp 1.10.1 into the user-level ask-codex state directory (`%LOCALAPPDATA%\ask-codex\chrome-devtools-mcp-1.10.1`) with `npm install --ignore-scripts` (no install script of the package runs; npm downloads from your configured registry), then checks every installed file against the hash manifest committed with ask-codex. An existing install is never replaced, only checked.
   - `installed`: keep `directory`; `changed` says whether it was installed now (`true`) or was already there and checked (`false`).
   - `failed`: report the reason and stop. When the reason says the installed server differs from the manifest, tell the user to remove the directory it names by hand and run the preparation again; never remove, edit or repair it yourself. On a host other than Windows the script refuses: exercises are Windows only.

2. **Check the dependencies:**

   ```bash
   python '<ask>/scripts/consult.py' exercise-deps
   ```

   It checks the installed browser server against the manifest again, finds node, and finds the Chrome the browser server would launch (stable channel) and its version. It does not start the browser server or Chrome: the first start is each exercise's browser guard, which stops the exercise before the app or Codex starts when the browser cannot start or its restrictions do not hold.
   - `ready`: report `node` (`node_version`), `chrome` (`chrome_version`) and `codex_version`. When `codex_untested` is `true`, also tell the user that their codex-cli (`codex_version`) is not the version this plugin was tested with (`codex_tested_version`), so how it approves the browser tools is untested, and that each exercise's confirmation will say so before anything starts.
   - `failed`: report the reason (for example Chrome missing or older than 149, node or npm missing) and stop.

3. **Report**: what was installed or checked, each dependency with its version, and that the machine is ready for `/ask-codex:ui` (or what is missing). Name the state directory (`%LOCALAPPDATA%\ask-codex`): it holds the browser server and the guard cache, never project data, and the user can delete it to remove both. Report in the conversation language.
