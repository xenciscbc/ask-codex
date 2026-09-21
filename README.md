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

A headless run needs its tool permissions spelled out; those are the flags the live acceptance runs used.

Installing from GitHub as a marketplace plugin is untested — the branch is published, but that flow has never been exercised, so only the command above is known to work.

## Prerequisites

- The Codex CLI, installed and logged in. If it is not logged in, Claude tells you to run `! codex login`.
- Verified against `codex-cli 0.154.0`. On the test machine `codex` resolved to the pnpm-installed `@openai/codex`, not the Codex desktop app's own binary — if both are installed, the one on your `PATH` is the one used.

## Usage

**Manual consultation.** Run `/ask-codex:ask` with or without a question, or just say it in your own words ("ask Codex about this", "get Codex's opinion"). Asking is itself the go-ahead. Without a question, Claude infers one from the conversation and shows it in one line before sending. ask-codex never consults Codex on its own: every consultation starts from your request.

**Consultation types.** Claude picks the type from context: a second opinion (challenge a plan or decision), a diagnosis (find a root cause when stuck), a targeted check (inspect a specific implementation or diff), a technical question, or a follow-up. Diagnoses and technical questions are sent **blind** — Claude's own hypothesis is withheld so the answer is not anchored.

**Models and effort.** Name a model by alias (`sol`, `astra`, `5.6 sol`) or with an effort (`sol:high`); an ambiguous alias makes Claude list the candidates and ask. Without a model, Claude uses the one chosen earlier in this session if there is one, otherwise the `model` in your Codex config, otherwise the highest-priority model Codex lists. Consultation effort is never below `medium` and is always passed explicitly, so Codex's own configured effort is not inherited. When your choice differs from the session's, an interactive session asks whether it applies to this consultation only or to the rest of the session; a headless run has no way to ask, so the choice applies to that consultation only and the reply says so on a line of its own: `Model choice applies to this consultation only: <model>, effort <effort>.` Naming the model the session already uses adds no such line.

**Parallel consultation.** Name two different models (`astra, sol`) to ask both the same question and get independent opinions, merged into consensus, solo claims and divergences, each tagged with the model that made it, and each divergence resolved with a stated reason. At most two models, never the same one twice.

**Follow-up consultation.** A follow-up runs in a fresh Codex session carrying the previous claims and Claude's dispositions, and asks Codex to report a status for each. It never resumes the earlier Codex session.

**Long runs.** Claude checks a running consultation every 30 minutes by default. While Codex is alive and producing events, it keeps waiting and says so in one line. If the run looks stalled, an interactive session asks whether to wait another interval or stop, showing the elapsed time and the last event with its age; a headless run has no way to ask, so it states the same information and stops. When a consultation is stopped, ask-codex ends the whole Codex process tree it started and reports the stop only after confirming that `events.jsonl` no longer changes; if it cannot confirm that, the report says the stop is not confirmed and lists the processes still alive, for you to deal with. Nothing is attributed to Codex after a stop. The plugin ships small scripts for this: one starts Codex as a process tree of its own and records it, one ends that tree and verifies that it is gone, and one waits for the run in the foreground. That last one matters in a headless run: a session whose tools include no `TaskOutput` cannot "wait for a notification" — its turn would end while Codex is still running, and the reply would never be read — so Claude blocks on the wait script instead, in chunks of at most nine minutes. Stopping was tested live with the real Codex CLI on Windows (Git Bash), in both an interactive and a headless session; on Linux it is covered by the scripts' offline test and the stubbed eval suite, not by a live Codex run; macOS is untested. The wait without `TaskOutput` is covered by the offline test on Windows and Linux and by stubbed eval cases in which the tool's absence is simulated by instruction (the eval harness cannot take it away); it has not been run live against the real Codex CLI.

**MCP policy.** By default every MCP server is disabled for each consultation (allowlist mode with an empty list). You can allow specific servers, or switch to minimal-deny mode where only `node_repl` and `cua_repl` are disabled. Settings live in an ask-codex config at the user level and optionally in the project, where the project's values override the user's; `/ask-codex:setup` helps you create them. Before every consultation Claude re-lists the servers as an MCP guard and aborts if what is actually enabled differs from the policy. A server defined by the project's own Codex config is never used without your explicit confirmation naming it.

## Known risks

- The safety statement above is the whole of it: read-only applies to Codex's **shell commands**, not to MCP servers.
- Codex's shell can read anything your account can read. The prompt limits its scope by instruction only.
- Any MCP server you allow runs outside the sandbox and may include tools that write or execute.
- Who may start a consultation is a rule Claude follows, not something the plugin enforces: there is no hook or tool-level block. In testing, text planted in a file started a consultation before a request check was added; with the check it was not seen again in a small number of runs, which is not proof that it cannot happen.
- A consultation costs roughly 25k input tokens before your question is even considered (an estimate from the design notes, not a measured figure).

## Known limitations

- A workspace on a drive where the Codex Windows sandbox cannot run is not consultable. Observed with a RAM disk: `codex exec -C R:\…` fails with `os error 1`. Claude reports the failure rather than inventing an answer.
- Projects trusted persistently in your Codex config are covered only by the project-layer fail-safe, which has not been tested live.
- About one stop in five to ten, the `Consultation stopped:` line appears only at the top of the final reply rather than at the moment of the stop (measured in the eval suite). The processes are ended either way.
- An external program can rewrite the `model` line in your Codex config while you work, and that line is what Claude uses when you name no model — so two consultations minutes apart can use different models with no action from you.

## License

MIT. See [LICENSE](./LICENSE).
