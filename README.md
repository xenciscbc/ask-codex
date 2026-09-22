# ask-codex

*[繁體中文版本](./README.zh-TW.md)*

Claude Code skills, also available as a plugin, that ask the local OpenAI Codex CLI for an independent opinion. Claude prepares the question, evaluates the answer, and gives each substantive claim a disposition: **adopt, reject or investigate**, with a reason. Implementation decisions remain with you and Claude.

## Current capabilities

- Five consultation types: second opinion, diagnosis, targeted check, technical question and follow-up. Diagnosis and technical questions withhold hypotheses to reduce anchoring.
- Model aliases and explicit reasoning effort; up to two different models can answer independently. Follow-ups use fresh sessions with prior claims and dispositions.
- Script-owned configuration, MCP authorization checks, execution, bounded waiting, process tracking and structured results.
- Unicode-safe result collection, recoverable output failures, and separate reporting of reply delivery and cleanup failures.
- Windows with Git Bash and Linux are the current implementation targets. Offline tests cover both; real-Claude validation is limited to two headless WSL cases using stub Codex. Full live Codex consultations and interactive flows are not yet validated for this implementation.

## Execution boundaries

Consultations invoke Codex with its read-only shell sandbox and shell network access blocked. MCP servers run outside that sandbox and are disabled by default. Any server you permit may expose tools that write or execute; the plugin does not make those tools read-only.

The skill instructs Claude to consult only when you request it and to treat Codex output as data. These are model instructions, not a hook or tool-level authorization barrier. Process termination also relies on observable process identities and snapshots, with the limitations described below.

## Installation and updates

Choose either a marketplace plugin or manually copied skills. Both use the prerequisites below.

### Option 1: Install from GitHub as a plugin

In Claude Code, add this repository's marketplace and install its plugin:

```text
/plugin marketplace add xenciscbc/ask-codex
/plugin install ask-codex@ask-codex
```

The first `ask-codex` is the plugin name; the second is the marketplace name defined in this repository. Then use `/ask-codex:ask` and `/ask-codex:setup`.

Alternatively, install from your terminal at user scope:

```bash
claude plugin marketplace add xenciscbc/ask-codex
claude plugin install ask-codex@ask-codex --scope user
```

To update that installation:

```bash
claude plugin marketplace update ask-codex
claude plugin update ask-codex@ask-codex --scope user
```

If you installed at `project` or `local` scope, use that scope instead. Restart Claude Code after installing or updating, or use `/reload-plugins` in a running session. Automatic updates can be enabled under `/plugin` → **Marketplaces** → **ask-codex** → **Enable auto-update**; third-party marketplaces do not enable them by default. See the official [installation guide](https://code.claude.com/docs/en/discover-plugins) and [plugin CLI reference](https://code.claude.com/docs/en/plugins-reference).

Release maintainers must increment `version` in `.claude-plugin/plugin.json` when publishing a plugin update. A Git tag alone does not change the installed plugin's version. See [version management](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels).

### Option 2: Copy the skills manually

Download or clone this repository, then copy these **entire directories**:

| Source | Personal installation | Project-only installation |
|---|---|---|
| `skills/ask/` | `~/.claude/skills/ask/` | `<project>/.claude/skills/ask/` |
| `skills/setup/` | `~/.claude/skills/setup/` | `<project>/.claude/skills/setup/` |

On Windows, `~` is your user home, typically `C:\Users\<username>`. The `ask` directory must include `SKILL.md`, `prompts/`, `scripts/` and `consultation.schema.json`; copying only `SKILL.md` is insufficient. `setup` provides the MCP policy setup helper.

With these directory names, use `/ask` and `/setup` instead of the plugin-prefixed commands shown elsewhere in this README. You can also explicitly ask Claude to consult Codex in natural language. See Claude Code's [skill locations and naming rules](https://code.claude.com/docs/en/skills).

To update, download or pull the latest repository and replace the installed directories with the matching new copies, including their supporting files. Back up any local edits first. Manually copied skills are not managed by `claude plugin update`.

### Local development and headless use

For testing a checkout without installing it:

```bash
claude --plugin-dir /path/to/ask-codex
```

For a headless run using that checkout:

```bash
claude -p --plugin-dir /path/to/ask-codex \
  --permission-mode acceptEdits \
  --allowedTools Bash Read Glob Grep Skill Write TaskOutput TaskStop \
  "/ask-codex:ask Why does fetchUser return an empty object on timeout?"
```

An installed plugin does not need `--plugin-dir`. Headless execution still needs the required tool permissions. The recorded real-Claude checks used local plugin loading under WSL with stub Codex; marketplace installation/update and manually copied skills have not been exercised end to end in this project's validation runs.

## Prerequisites

- Claude Code with skill or plugin support and permission to run the required file and Bash tools.
- Python 3.11 or newer. The consultation script uses the standard library's `tomllib` to read Codex configuration.
- Bash. Linux uses Bash directly; Windows requires Git Bash.
- The Codex CLI, installed and logged in. If it is not logged in, Claude tells you to run `! codex login`.
- The previous implementation was verified against `codex-cli 0.154.0`. On that test machine `codex` resolved to the pnpm-installed `@openai/codex`, not the Codex desktop app's own binary — if both are installed, the one on your `PATH` is the one used.

## Usage

```text
/ask-codex:ask Why does fetchUser return an empty object on timeout?
/ask-codex:ask sol:high Check the retry logic in this diff.
/ask-codex:ask astra, sol Give a second opinion on this plan.
/ask-codex:setup
```

Aliases resolve against your local Codex model list; these examples do not guarantee model availability.

**Manual consultation.** Run `/ask-codex:ask` with or without a question, or just say it in your own words ("ask Codex about this", "get Codex's opinion"). Asking is itself the go-ahead. Without a question, Claude infers one from the conversation and shows it in one line before sending. The skill requires your own request for each consultation; the enforcement boundary is described above.

**Consultation types.** Claude picks the type from context: a second opinion (challenge a plan or decision), a diagnosis (find a root cause when stuck), a targeted check (inspect a specific implementation or diff), a technical question, or a follow-up. Diagnoses and technical questions are sent **blind** — Claude's own hypothesis is withheld so the answer is not anchored.

**Models and effort.** Name a model by alias (`sol`, `astra`, `5.6 sol`) or with an effort (`sol:high`); an ambiguous alias makes Claude list the candidates and ask. Without a model, Claude uses the one chosen earlier in this session if there is one, otherwise the `model` in your Codex config, otherwise the highest-priority visible model in the local cache; if no model is available from these sources, the CLI selects its default. Consultation effort is never below `medium` and is always passed explicitly, rather than inherited from Codex configuration. `ultra` requires an explicit request and model support. When your choice differs from the session's, an interactive session asks whether it applies to this consultation only or to the rest of the session. A headless run cannot ask, so the choice applies only to that consultation and the report discloses the scope in the conversation language; no fixed sentence or line position is required. Naming the model and effort already in use needs no scope note.

**Parallel consultation.** Name two different models (`astra, sol`) to ask both the same question and get independent opinions, merged into consensus, solo claims and divergences, each tagged with the model that made it, and each divergence resolved with a stated reason. At most two models, never the same one twice.

**Follow-up consultation.** A follow-up runs in a fresh Codex session carrying the previous claims and Claude's dispositions, and asks Codex to report a status for each. It never resumes the earlier Codex session.

**Script-owned execution and long runs.** Claude prepares the question and judges the answer, while [`skills/ask/scripts/consult.py`](skills/ask/scripts/consult.py) owns policy resolution, preflight checks, safe command construction, process lifecycle and structured status. It prepares a reviewable summary of the model and effort, project directory, allowed MCP servers and policy before launch. Its statuses distinguish pending confirmation, preflight failure, running, completion, execution failure, confirmed stop and unconfirmed stop; a runtime failure is never treated as a Codex opinion.

Claude checks a running consultation every 30 minutes by default, using foreground waits of no more than 60 seconds and never exceeding the remaining check interval. If the run looks stalled, an interactive session shows elapsed time and the last event and asks whether to wait another interval or stop; a headless run reports the same information and follows the stop path. The scripts report a confirmed stop when their process-identity and tree checks pass; this is bounded by the snapshot limitations below. An unconfirmed stop preserves its control files and diagnostics, including anything a surviving process may still use, and reports their location. Those diagnostics have no automatic expiry and are removed only after an explicit cleanup request; logs may contain project content. Prompts and replies are removed once termination is confirmed rather than retained as long-term diagnostics.

**Result delivery and recovery.** Collection writes and flushes the complete reply as ASCII-safe JSON before deleting successful run files, preserving Unicode content even with legacy Windows output encodings. If output delivery fails, the files remain so Claude can collect the same result again without starting another consultation. If cleanup fails after delivery, Claude reports the valid reply and retained location separately. There is no automatic retry after a model starts.

**MCP policy.** By default every MCP server is disabled for each consultation (allowlist mode with an empty list). You can allow specific servers, or switch to minimal-deny mode where only `node_repl` and `cua_repl` are disabled. Settings live in an ask-codex config at the user level and optionally in the project, where the project's values override the user's; `/ask-codex:setup` helps you create them. Missing policy files use the documented fallback, while an existing file with invalid JSON, types, policy values or server names fails closed before Codex starts. The script checks the effective MCP state before execution and supports literal server names containing dots.

Policy files are merged key by key:

| Scope | File |
|---|---|
| User | `~/.claude/ask-codex.json` |
| Project | `<project>/.claude/ask-codex.local.json` |

For example, this policy permits only a server named `docs` if it is already enabled in Codex:

```json
{"mcp_policy": "allowlist", "mcp_allow": ["docs"]}
```

The setup skill writes ask-codex policy files; it does not edit Codex's `config.toml`. Keep the project-local policy out of version control. Project policy and server-use changes can require session confirmation during preparation; unresolved confirmations prevent headless execution.

A project-defined server needs explicit source confirmation, bound to that exact definition. Changing its command, arguments, endpoint, environment or other definition fields invalidates the earlier confirmation. Source confirmation only acknowledges the definition; permission to use the server is a separate decision, although Claude may ask for both clearly in one question. Confirmation IDs come from the prepared definition and cannot themselves grant consent.

## Verification

Validation recorded on **2026-09-22**, through implementation commit `7381fdc`:

| Check | Windows / Git Bash | Linux / Ubuntu WSL |
|---|---|---|
| Public CLI integration with stub Codex | 25 tests passed | 25 tests passed |
| Process lifecycle checks | 39 assertions passed (elevated) | 46 assertions passed |
| Complete offline Node inventory | 18 test files passed | Full inventory not rerun for the final fix |
| Real Claude headless with stub Codex | Not verified | Two focused cases passed, one run each |
| Full consultation with real Codex | Not verified | Not verified |
| Interactive Claude flows | Not verified | Not verified |

Run the public CLI and focused lifecycle checks with Python 3.11+ and Node.js:

```bash
python evals/_harness/consultation_test.py
node evals/_harness/process-lifecycle.test.mjs
```

On Linux, use `python3` if that is your Python 3.11+ interpreter. These suites use local stub processes, not the Codex service. The lifecycle suite deliberately launches and stops test processes; Windows verification depends on process-query permissions.

The two real-Claude WSL cases were `script-consultation` (3/3 graders) and `script-confirmation` (2/2 graders), each scoring 1.00. They ran during the initial script-owned implementation and were not repeated after the lifecycle fixes. Isolated real `codex mcp list` probes also checked disabling dotted server names; they did not run a consultation.

See the [validation record](.scratch/script-owned-consultation/evidence/validation.md) for commands, reports, regression history and remaining acceptance gaps. Historical evals for the previous implementation are not proof of current behavior. macOS is outside the current acceptance scope.

## Known risks and limitations

- **MCP access:** allowed tools execute outside the shell sandbox. Prompt instructions cannot enforce read-only behavior inside those tools. Read-only shell execution also does not itself constrain access to only the files relevant to your question.
- **Request provenance:** consultation and confirmation require your own request under the skill's rules, but that rule depends on Claude following instructions. Earlier tests exposed a file-originated request before a request check was added; the limited subsequent checks do not prove immunity to prompt injection.
- **Process snapshots:** tracking covers observed descendants, including captured detached children, and checks identities before individual signals. A child that detaches and is reparented before observation can escape discovery. If a PID/group is reused and its replacement leader exits before observation, the remaining group may be mistaken for the original group and signalled. The plugin does not provide kernel-enforced process ownership.
- **Unconfirmed stops:** processes may remain alive when enumeration or identity checks are unavailable, including restricted Windows process-query permissions. Keep the reported diagnostics; root exit or a quiet log alone does not prove termination.
- **Retained content:** unresolved stops retain files a process may still need. Error logs may contain project content. Diagnostic cleanup requires an explicit request and confirmed termination; there is no automatic expiry.
- **Platform and configuration:** a historical Windows RAM-disk test failed with `os error 1`; that is not a diagnosis for every OS error. Persistently trusted project definitions have not been validated end to end with the real Codex CLI. When no session model is selected, an external change to the configured model can affect the next consultation.
- **Cost:** consultations consume Codex usage, and a parallel pair starts two runs. Current per-consultation token overhead has not been measured.

Reports may follow the conversation language. They must still include the question and type, model and effort, effective MCP policy, relevant timer/stop details, and Claude's disposition for each substantive claim. Execution failures contribute no attributed Codex opinion.

## License

MIT. See [LICENSE](./LICENSE).
