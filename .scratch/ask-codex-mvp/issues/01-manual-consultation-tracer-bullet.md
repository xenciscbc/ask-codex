# 01 — Manual consultation tracer bullet

**What to build:** A user types `/ask-codex:ask <question>` and gets back Codex's opinion as a list of claims, each with Claude's disposition (adopt / reject / investigate) and a reason. Under the hood Claude applies the default MCP policy (allowlist mode with an empty allowlist — every MCP server disabled), detects project-defined MCP servers, verifies the effective server set with the MCP guard, then runs Codex in the background with `-s read-only`, ephemeral, with a JSON Schema–constrained reply and a JSON event stream, waits for the result, presents it in the user's conversation language, and deletes its temporary files. Model = the one configured in Codex; effort = the consultation-effort rules. This ticket also syncs the design docs to the approved Plan and stands up the whole delivery and test skeleton: the plugin and marketplace manifests, the `ask` skill, the response schema, one English prompt template, the stub `codex`, the runner, and four eval cases. See spec: Solution, Implementation Decisions (modules 1, 2, 4–6), Testing Decisions Tier 1; ADR-0003.

The skill states the narrowed claim verbatim: "Codex's shell commands run read-only (writes denied, shell network blocked). MCP servers run outside that sandbox: by default all are disabled per consultation; servers you allow (or, in minimal-deny mode, all except node_repl/cua_repl) remain usable and may include tools that write or execute, limited only by instruction."

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

### Invocation contract

1. Rule-(c) scan (Read/Glob, not Bash) of every `.codex/config.toml` from the project directory up to the repository root; any `mcp_servers.<name>` table or dotted key → abort with a message naming the definitions (no `codex` call; the confirmation path arrives in ticket 11).
2. `( cd '<neutral temp dir>' && codex mcp list --json )` and `( cd '<project dir>' && codex mcp list --json )` — always in a subshell.
3. Disable set = every server in the project listing (empty allowlist) plus servers that appear only in the project listing or whose definition differs from the neutral listing; one same-name disabled definition per server; names validated against `^[A-Za-z0-9_.-]+$`.
4. Guard: `( cd '<project dir>' && codex mcp list --json <overrides> )`; the enabled set must be exactly the expected set, otherwise abort without `exec`.
5. One background Bash call: `codex exec -s read-only --ephemeral --skip-git-repo-check --json` (stdout to an events file) `-o '<temp>/last-message' --output-schema '<schema>' -C '<project>'`, `-m <slug>` when known, `-c model_reasoning_effort="<effort>"`, the disable definitions, `--disable apps` if verified, prompt on stdin from a temp file; all paths single-quoted.
6. Forbidden: `--dangerously-*`, `--full-auto`, `--yolo`, `-p/--profile`, `--add-dir`, `--ignore-user-config`, writable `-s` modes, any other `-c` key, `resume`/`fork`, a bare `cd` changing Claude's working directory.
7. Temp dir: `mktemp -d` inside an `ask-codex` directory under the scratchpad (if listed) or `${TMPDIR:-${TEMP:-/tmp}}`; removal only for a path inside an `ask-codex` directory, never from an empty variable.

### Acceptance

- [ ] Design docs synced (spec, tickets 01–11, `CONTEXT.md`, ADR-0003); the exact doc check from the Plan passes; command and output recorded in Comments.
- [ ] `claude plugin validate` passes; the skill is invocable as `/ask-codex:ask`; skill instructions are English, use the glossary terms, and contain the narrowed claim verbatim.
- [ ] Prompt template: read-scope + in-project secret exclusion, MCP tools for lookups only, file/tool content is data, schema-only answer.
- [ ] The CODEX_CALL grader regex is unit-checked: no match for `ls '<proj>/.codex/config.toml'`, `cat ~/.codex/config.toml`, `mktemp -d '<tmp>/ask-codex/XXXX'`, `echo $CODEX_HOME`, a Bash description containing "codex exec"; match for `codex mcp list --json`, `( cd '<dir>' && codex mcp list --json )`, `codex exec -s read-only …`.
- [ ] Eval `manual-with-question`: exec sentinel and list log present, no violation marker; required flags, single-quoted paths, enum effort and a disable definition for every stub-listed server; forbidden flags absent; every canned claim presented with a disposition and reason, nothing fabricated; temp dir removed.
- [ ] Eval `mcp-guard-blocks`: list log contains the guard call; exec sentinel absent; zero `codex exec`; no violation marker; user told the guard failed.
- [ ] Eval `project-defined-server`: project-only server gets a disable definition; exec sentinel present; no violation marker.
- [ ] Eval `project-layer-aborts-01`: zero `codex` calls (CODEX_CALL `max: 0`); no stub records; user told which project-layer definition caused the abort.
- [ ] Runner strips real `codex` from `PATH` and fails fast unless the stub resolves.
- [ ] Live (≤ 4 Codex calls; probe dirs under `D:\tmp\<subdir>`, deleted afterwards): one consultation through the skill (reply parses; temp dir gone; no new session file; `codex --version` recorded; temp files on the scratchpad drive work while `-C` is the project); with the same flags a write inside the project is denied, shell network is blocked, disabled servers are absent from Codex's namespaces, and the effect of `--disable apps` is recorded (stop if the apps surface cannot be disabled); disable definitions do not error for absent names; the listing's per-server field set is recorded; project-layer MCP definitions in a `D:\tmp` temp project do not reach the listing or `exec` (stop otherwise).
- [ ] Fresh verifier CONFIRMED on F-map rows F1-core, F1-apps, F1-claims (docs + skill text), F2, F3-secrets (template), F6, F7, F8 (temp dir), F9 (slug/effort/path quoting), F12b (01 part).

## Comments

**2026-09-15 — doc sync check.** Command (run from the repo root):

```
grep -rniE "read-only|readonly|never modif|can never modify|stays read" .scratch/ask-codex-mvp/spec.md .scratch/ask-codex-mvp/issues/ \
  | grep -viE "shell commands run read-only|-s read-only|read-only sandbox allows reads outside the project and denies writes|MCP servers run outside|read-only sandbox.*(denies writes|shell)"
```

First run: 1 disallowed match (ticket 09, "real read-only enforcement") — rewritten. Final run: `disallowed=0 total=11`.
