# ask-codex

*[繁體中文版本](./README.zh-TW.md)*

A Claude Code plugin that lets Claude **consult** OpenAI Codex through the local Codex CLI for an independent opinion, and then judge every claim itself. Codex answers and never edits anything itself, with one caveat worth reading below: MCP servers run outside Codex's read-only sandbox. Every decision and every change stays with Claude and you — this is a consultation, not a delegation.

Codex returns its opinion as structured **claims**, and Claude gives each one a **disposition** — adopt, reject or investigate — with a reason.

## What you can rely on

> Codex's shell commands run read-only (writes denied, shell network blocked). MCP servers run outside that sandbox: by default all are disabled per consultation; servers you allow (or, in minimal-deny mode, all except node_repl/cua_repl) remain usable and may include tools that write or execute, limited only by instruction.

## Installation

Clone this repository and load it as a plugin:

```bash
claude --plugin-dir /path/to/ask-codex
```

The same flag works for a headless run:

```bash
claude -p --plugin-dir /path/to/ask-codex \
  --permission-mode acceptEdits \
  --allowedTools Bash Read Glob Grep Skill Write TaskOutput TaskStop \
  "/ask-codex:ask Why does fetchUser return an empty object on timeout?"
```

A headless run needs its tool permissions spelled out. The script-owned workflow has been exercised through real Claude headless under WSL Ubuntu with a stub Codex CLI; this example has not been accepted end to end with the real Codex CLI.

Installing from GitHub as a marketplace plugin is untested — the branch is published, but that flow has never been exercised, so only the command above is known to work.

## Prerequisites

- Python 3.11 or newer. The consultation script uses the standard library's `tomllib` to read Codex configuration.
- Bash. Linux uses Bash directly; Windows requires Git Bash.
- The Codex CLI, installed and logged in. If it is not logged in, Claude tells you to run `! codex login`.
- The previous implementation was verified against `codex-cli 0.154.0`. On that test machine `codex` resolved to the pnpm-installed `@openai/codex`, not the Codex desktop app's own binary — if both are installed, the one on your `PATH` is the one used.

## Usage

**Manual consultation.** Run `/ask-codex:ask` with or without a question, or just say it in your own words ("ask Codex about this", "get Codex's opinion"). Asking is itself the go-ahead. Without a question, Claude infers one from the conversation and shows it in one line before sending. ask-codex never consults Codex on its own: every consultation starts from your request.

**Consultation types.** Claude picks the type from context: a second opinion (challenge a plan or decision), a diagnosis (find a root cause when stuck), a targeted check (inspect a specific implementation or diff), a technical question, or a follow-up. Diagnoses and technical questions are sent **blind** — Claude's own hypothesis is withheld so the answer is not anchored.

**Models and effort.** Name a model by alias (`sol`, `astra`, `5.6 sol`) or with an effort (`sol:high`); an ambiguous alias makes Claude list the candidates and ask. Without a model, Claude uses the one chosen earlier in this session if there is one, otherwise the `model` in your Codex config, otherwise the highest-priority model Codex lists. Consultation effort is never below `medium` and is always passed explicitly, so Codex's own configured effort is not inherited. When your choice differs from the session's, an interactive session asks whether it applies to this consultation only or to the rest of the session. A headless run cannot ask, so the choice applies only to that consultation and the report discloses the scope in the conversation language; no fixed sentence or line position is required. Naming the model and effort already in use needs no scope note.

**Parallel consultation.** Name two different models (`astra, sol`) to ask both the same question and get independent opinions, merged into consensus, solo claims and divergences, each tagged with the model that made it, and each divergence resolved with a stated reason. At most two models, never the same one twice.

**Follow-up consultation.** A follow-up runs in a fresh Codex session carrying the previous claims and Claude's dispositions, and asks Codex to report a status for each. It never resumes the earlier Codex session.

**Script-owned execution and long runs.** Claude prepares the question and judges the answer, while `scripts/consult.py` owns policy resolution, preflight checks, safe command construction, process lifecycle and structured status. It prepares a reviewable summary of the model and effort, project directory, allowed MCP servers and policy before launch. Its statuses distinguish pending confirmation, preflight failure, running, completion, execution failure, confirmed stop and unconfirmed stop; a runtime failure is never treated as a Codex opinion.

Claude checks a running consultation every 30 minutes by default, using foreground waits of no more than 60 seconds and never exceeding the remaining check interval. If the run looks stalled, an interactive session shows elapsed time and the last event and asks whether to wait another interval or stop; a headless run reports the same information and follows the stop path. A stop is reported as confirmed only after the process tree is verified ended. An unconfirmed stop preserves its control files and diagnostics, including anything a surviving process may still use, and reports their location. Those diagnostics have no automatic expiry and are removed only after an explicit cleanup request; logs may contain project content. Prompts and replies are removed once termination is confirmed rather than retained as long-term diagnostics.

**MCP policy.** By default every MCP server is disabled for each consultation (allowlist mode with an empty list). You can allow specific servers, or switch to minimal-deny mode where only `node_repl` and `cua_repl` are disabled. Settings live in an ask-codex config at the user level and optionally in the project, where the project's values override the user's; `/ask-codex:setup` helps you create them. Missing policy files use the documented fallback, while an existing file with invalid JSON, types, policy values or server names fails closed before Codex starts. The script checks the effective MCP state before execution and supports literal server names containing dots.

A project-defined server needs explicit source confirmation, bound to that exact definition. Changing its command, arguments, endpoint, environment or other definition fields invalidates the earlier confirmation. Source confirmation only acknowledges the definition; permission to use the server is a separate decision, although Claude may ask for both clearly in one question. Confirmation IDs come from the prepared definition and cannot themselves grant consent.

## Verification

The public stub-CLI integration suite has been exercised on Windows and Linux with:

```bash
python evals/_harness/consultation_test.py
```

On 2026-09-22, real Claude headless under WSL Ubuntu ran each new focused eval once against the stub Codex CLI. `script-consultation` passed all 3 graders with score 1, and `script-confirmation` passed both graders with score 1:

```bash
evals/_harness/run-evals.sh --case script-consultation --runs 1 --allow-tools Bash Write
evals/_harness/run-evals.sh --case script-confirmation --runs 1 --allow-tools Bash Write
```

The public CLI suite passes 25 tests on each platform. See [validation evidence](.scratch/script-owned-consultation/evidence/validation.md) for lifecycle results, review fixes, instruction-size measurements and remaining gaps. Earlier eval cases and historical live Windows results exercise the previous implementation and are not current acceptance evidence. Isolated real `codex mcp list` probes verified that a dotted server name can be disabled, but no full consultation with the real Codex CLI has been verified. Interactive Claude flows also remain unverified. macOS is outside the supported acceptance scope.

## Known risks

- The safety statement above is the whole of it: read-only applies to Codex's **shell commands**, not to MCP servers.
- Codex's shell can read anything your account can read. The prompt limits its scope by instruction only.
- Any MCP server you allow runs outside the sandbox and may include tools that write or execute.
- Who may start a consultation is a rule Claude follows, not something the plugin enforces: there is no hook or tool-level block. In testing, text planted in a file started a consultation before a request check was added; with the check it was not seen again in a small number of runs, which is not proof that it cannot happen.
- An unconfirmed stop can leave processes alive. ask-codex reports that uncertainty and retains the run files needed for diagnosis rather than claiming the consultation ended.
- A consultation costs roughly 25k input tokens before your question is even considered (an estimate from the design notes, not a measured figure).

## Known limitations

- A workspace on a drive where the Codex Windows sandbox cannot run is not consultable. Observed with a RAM disk: `codex exec -C R:\…` fails with `os error 1`. Claude reports the failure rather than inventing an answer.
- Persistently trusted projects still rely on the script's project-definition checks; that path has not been verified end to end with the real Codex CLI.
- An external program can rewrite the `model` line in your Codex config while you work, and that line is what Claude uses when you name no model — so two consultations minutes apart can use different models with no action from you.

Reports may follow the conversation language and wording. There is no required English heading or fixed line position, but the report must preserve the question and consultation type, model and effort, effective MCP policy, relevant timer and stop details, and Claude's disposition for each substantive claim.

## License

MIT. See [LICENSE](./LICENSE).
