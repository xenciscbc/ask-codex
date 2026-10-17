# ask-codex

*[繁體中文版本](./README.zh-TW.md)*

Claude Code skills, also available as a plugin, that ask the local OpenAI Codex CLI for an independent opinion. Claude prepares the question, evaluates the answer, and gives each substantive claim a disposition: **adopt, reject or investigate**, with a reason. Implementation decisions remain with you and Claude.

## Current capabilities

- Five consultation types: second opinion, diagnosis, targeted check, technical question and follow-up. Diagnosis and technical questions withhold hypotheses to reduce anchoring.
- Model aliases and explicit reasoning effort; up to two different models can answer independently. Follow-ups use fresh sessions with prior claims and dispositions.
- Script-owned configuration, MCP authorization checks, execution, bounded waiting, process tracking and structured results.
- Unicode-safe result collection, recoverable output failures, and separate reporting of reply delivery and cleanup failures.
- Whole-change review: `/ask-codex:review` sends the working tree, a branch against a base, or a commit range to Codex; Claude judges every claim. Only you can start it, by typing the command.
- Multi-round discussion: `/ask-codex:discuss` has Claude and one Codex model work a design topic over several rounds — independent first answers, then only the disputed points — and reports what was agreed and what is left for you to decide, with each side's recommendation. Only you can start it, by typing the command.
- UI exercise: `/ask-codex:ui` lets Codex operate your web app in an isolated, network-restricted Chrome — on a disposable copy of the project, or, when you ask for it, on the dev servers you already run — and reports bugs, layout problems and UX suggestions; Claude reproduces every bug claim through the same restricted browser and judges every claim. Only you can start it, by typing the command. Windows only. See [UI exercise](#ui-exercise-ask-codexui).
- Windows with Git Bash and Linux are the current implementation targets for consultations, reviews and discussions; the UI exercise is Windows only. Offline tests cover both; real-Claude validation is limited to two headless WSL cases using stub Codex. Full live Codex consultations and interactive flows are not yet validated for this implementation.

## Execution boundaries

Consultations invoke Codex with its read-only shell sandbox, with child agents switched off (`-c agents.enabled=false -c features.multi_agent_v2.enabled=false`, since 1.3.2 — see the known risk "Child agents" below), with escalation out of the sandbox refused (`-c approval_policy="never" -c approvals_reviewer="user"`, since 1.3.3 — see "Approval escalation") and without loading execpolicy `.rules` files (`--ignore-rules`, since 1.3.3). The shell sandbox blocks writes and outbound network; on Windows it does not block loopback, so shell commands can reach every localhost service on the machine (see "Localhost services"). MCP servers run outside that sandbox; by default, the script disables every server observed during preflight. Configuration changes between preflight and execution can escape that check, as described below. Any server you permit may expose tools that write or execute; the plugin does not make those tools read-only.

A UI exercise is a separate interaction with its own boundary ([ADR 0009](docs/adr/0009-exercise-on-a-disposable-target.md)): the same read-only shell and command-line constants, every MCP server disabled except one pinned, restricted browser server whose listed tools are approved per tool, and a disposable target that is removed afterwards. Codex and its browser never write to your project. See [UI exercise](#ui-exercise-ask-codexui) for what that boundary does and does not cover.

The skill instructs Claude to consult only when you request it and to treat Codex output as data. These are model instructions, not a hook or tool-level authorization barrier. Process termination also relies on observable process identities and snapshots, with the limitations described below.

## Installation and updates

Choose either a marketplace plugin or manually copied skills. Both use the prerequisites below.

### Option 1: Install from GitHub as a plugin

In Claude Code, add this repository's marketplace and install its plugin:

```text
/plugin marketplace add xenciscbc/ask-codex
/plugin install ask-codex@ask-codex
```

The first `ask-codex` is the plugin name; the second is the marketplace name defined in this repository. Then use `/ask-codex:ask`, `/ask-codex:review`, `/ask-codex:discuss`, `/ask-codex:ui` and `/ask-codex:setup`.

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
| `skills/review/` | `~/.claude/skills/review/` | `<project>/.claude/skills/review/` |
| `skills/discuss/` | `~/.claude/skills/discuss/` | `<project>/.claude/skills/discuss/` |
| `skills/setup/` | `~/.claude/skills/setup/` | `<project>/.claude/skills/setup/` |
| `skills/ui/` | `~/.claude/skills/ui/` | `<project>/.claude/skills/ui/` |

On Windows, `~` is your user home, typically `C:\Users\<username>`. The `ask` directory must include `SKILL.md`, `prompts/`, `scripts/`, `consultation.schema.json`, `discussion.schema.json`, `ui-exercise.schema.json`, `browser-server/` and `guard-page/`; copying only `SKILL.md` is insufficient. `setup` provides the MCP policy setup helper and prepares a machine for UI exercises. `review`, `discuss` and `ui` run through the `ask` skill's scripts and prompts, which they find as their sibling directory (`../ask`), so copy them only together with `ask`, into the same parent directory.

With these directory names, use `/ask`, `/review`, `/discuss`, `/ui` and `/setup` instead of the plugin-prefixed commands shown elsewhere in this README. You can also explicitly ask Claude to consult Codex in natural language. See Claude Code's [skill locations and naming rules](https://code.claude.com/docs/en/skills).

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
- For `/ask-codex:ui` only: Windows, Google Chrome (stable channel) 149 or later, and Node.js with its bundled npm on your `PATH`. Run `/ask-codex:setup` once and ask it to prepare for exercises: it installs the pinned browser server and checks these (see [UI exercise](#ui-exercise-ask-codexui)). The exercise was tested with `codex-cli 0.159.3`.
- The previous implementation was verified against `codex-cli 0.154.0`. On that test machine `codex` resolved to the pnpm-installed `@openai/codex`, not the Codex desktop app's own binary — if both are installed, the one on your `PATH` is the one used.

## Usage

```text
/ask-codex:ask Why does fetchUser return an empty object on timeout?
/ask-codex:ask sol:high Check the retry logic in this diff.
/ask-codex:ask astra, sol Give a second opinion on this plan.
/ask-codex:review
/ask-codex:review --base main
/ask-codex:review sol main..HEAD check error handling
/ask-codex:discuss How should the login service limit password guessing?
/ask-codex:discuss sol:high rounds 5 Design the plugin's settings file format.
/ask-codex:ui
/ask-codex:ui sol:high --headed the checkout flow
/ask-codex:setup
```

Aliases resolve against your local Codex model list; these examples do not guarantee model availability.

**Manual consultation.** Run `/ask-codex:ask` with or without a question, or just say it in your own words ("ask Codex about this", "get Codex's opinion"). Asking is itself the go-ahead. Without a question, Claude infers one from the conversation and shows it in one line before sending. The skill requires your own request for each consultation; the enforcement boundary is described above.

**Consultation types.** Claude picks the type from context: a second opinion (challenge a plan or decision), a diagnosis (find a root cause when stuck), a targeted check (inspect a specific implementation or diff), a technical question, or a follow-up. Diagnoses and technical questions are sent **blind** — Claude's own hypothesis is withheld so the answer is not anchored.

**Models and effort.** Name a model by alias (`sol`, `astra`, `6 sol`) or with an effort (`sol:high`); an ambiguous alias makes Claude list the candidates and ask. Without a model, Claude uses the one chosen earlier in this session if there is one, otherwise the `model` in your Codex config, otherwise the highest-priority visible model in the local cache; if no model is available from these sources, the CLI selects its default. Consultation effort is never below `medium` and is always passed explicitly, rather than inherited from Codex configuration. `ultra` requires an explicit request and model support. When your choice differs from the session's, an interactive session asks whether it applies to this consultation only or to the rest of the session. A headless run cannot ask, so the choice applies only to that consultation and the report discloses the scope in the conversation language; no fixed sentence or line position is required. Naming the model and effort already in use needs no scope note.

**Review.** `/ask-codex:review [model tokens] [--base <ref> | A..B | A...B] [focus]` consults Codex about one whole change. The scope is the working tree by default (staged, unstaged and untracked files); `--base <b>` means the commits on `HEAD` since its merge base with `<b>` (committed changes only; uncommitted changes are not included); `A..B` and `A...B` name an explicit commit range. Any remaining text is your focus, passed to Codex verbatim. Model tokens work as in `ask`, including two models in parallel. Claude resolves each ref with hardened, read-only git commands (an option-like ref is rejected, and nothing runs when the scope is empty or rejected), gives Codex the scope and the change's intent as its stance, and lets Codex inspect the diff itself, read-only. The report begins with the scope line, then lists every claim with Claude's disposition. A review with no claims is not an approval. **It is user-only:** the skill disables model invocation, so Claude cannot start it and only typing the command does; natural-language review requests are not turned into reviews. Asked for a whole-change review, `ask` tells you the command exists instead. Claude never fixes anything because of a claim.

**Discussion.** `/ask-codex:discuss [model token] [rounds <n>] [topic]` works one topic — a feature design, an interface, a workflow — with one Codex model over several rounds. In round 1 both sides answer independently: Claude writes its own result down before Codex starts, and Codex never sees it. Claude then integrates the two: points both raised become tentative agreements, Codex's points Claude agrees with join them, and the rest — Codex's points Claude disputes and Claude's own points — are contested. Each later round sends only the contested points, with both sides' full reasons and evidence, to a **fresh** Codex session (never a resumed one; see [ADR 0007](docs/adr/0007-discuss-skill.md)); Codex accepts, maintains or revises each, and Claude answers in turn. The discussion ends when nothing is contested or at the round limit: `rounds <n>` (2–10) in the command, otherwise Claude asks (3, 5, 7 or your own number), and a headless run uses 3 and says so. The report has three parts: the process (one or two lines per round, who was persuaded by what), what was agreed (including points both sides dropped), and what is for you to decide — points still split at the end and points both sides consider your preference or authority — each with Claude's and Codex's recommendation and reason. To resist false agreement, a concession must cite specific evidence or is labelled an *unevidenced concession*, points that flip in round 3 or later are flagged, new points after round 1 are allowed only when they would change the conclusion, and these rules bind Claude as well as Codex. A round that fails, is stopped or returns an unstructured reply ends the discussion with a partial report; nothing is retried. Only one model takes part, fixed for the whole discussion. **It is user-only**, like review: Claude cannot start it, and asked in natural language, `ask` points you to the command. Codex reads only, under the same MCP policy as `ask`, checked before every round; when a topic needs outside documentation, allow a documentation MCP server as described under MCP policy below.

**Parallel consultation.** Name two different models (`astra, sol`) to ask both the same question and get independent opinions, merged into consensus, solo claims and divergences, each tagged with the model that made it, and each divergence resolved with a stated reason. At most two models, never the same one twice.

**Follow-up consultation.** A follow-up runs in a fresh Codex session carrying the previous claims and Claude's dispositions, and asks Codex to report a status for each. It never resumes the earlier Codex session.

**Script-owned execution and long runs.** Claude prepares the question and judges the answer, while [`skills/ask/scripts/consult.py`](skills/ask/scripts/consult.py) owns policy resolution, preflight checks, safe command construction, process lifecycle and structured status. It prepares a reviewable summary of the model and effort, project directory, allowed MCP servers and policy before launch. Its statuses distinguish pending confirmation, preflight failure, running, completion, execution failure, confirmed stop and unconfirmed stop; a runtime failure is never treated as a Codex opinion.

Claude checks a running consultation every 30 minutes by default, using foreground waits of no more than 60 seconds and never exceeding the remaining check interval. If the run looks stalled, an interactive session shows elapsed time and the last event and asks whether to wait another interval or stop; a headless run reports the same information and follows the stop path. The scripts report a confirmed stop when their process-identity and tree checks pass; this is bounded by the snapshot limitations below. An unconfirmed stop preserves its control files and diagnostics, including anything a surviving process may still use, and reports their location. Those diagnostics have no automatic expiry and are removed only after an explicit cleanup request; logs may contain project content. Prompts and replies are removed once termination is confirmed rather than retained as long-term diagnostics.

**Result delivery and recovery.** Collection writes and flushes the complete reply as ASCII-safe JSON before deleting successful run files, preserving Unicode content even with legacy Windows output encodings. If output delivery fails, the files remain so Claude can collect the same result again without starting another consultation. If cleanup fails after delivery, Claude reports the valid reply and retained location separately. There is no automatic retry after a model starts.

**MCP policy.** By default the script disables every MCP server observed during preflight (allowlist mode with an empty list), subject to the configuration-race limitation below. You can allow specific servers, or switch to minimal-deny mode where only `node_repl` and `cua_repl` are disabled. Settings live in an ask-codex config at the user level and optionally in the project, where the project's values override the user's; `/ask-codex:setup` helps you create them. Missing policy files use the documented fallback, while an existing file with invalid JSON, types, policy values or server names fails closed before Codex starts. The script checks the effective MCP state before execution and supports literal server names containing dots.

Policy files are merged key by key:

| Scope | File |
|---|---|
| User | `~/.claude/ask-codex.json` |
| Project | `<project>/.claude/ask-codex.local.json` |

Server names are the names Codex itself uses: `codex mcp list` shows them, and `/ask-codex:setup` lists them for you. For example, this policy permits only a server named `docs` if it is already enabled in Codex:

```json
{"mcp_policy": "allowlist", "mcp_allow": ["docs"]}
```

The setup skill writes ask-codex policy files; it does not edit Codex's `config.toml`. Keep the project-local policy out of version control. Project policy and server-use changes can require session confirmation during preparation; unresolved confirmations prevent headless execution.

A project-defined server needs explicit source confirmation, bound to that exact definition. Changing its command, arguments, endpoint, environment or other definition fields invalidates the earlier confirmation. Source confirmation only acknowledges the definition; permission to use the server is a separate decision, although Claude may ask for both clearly in one question. Confirmation IDs come from the prepared definition and cannot themselves grant consent.

## UI exercise (`/ask-codex:ui`)

`/ask-codex:ui [model token] [--headed] [scope or focus]` lets Codex use your web app instead of reading its code. Codex operates the app in an isolated Chrome — navigates, clicks, fills forms, resizes to several viewports including a phone size, takes screenshots and looks at them, reads the browser console and network log — and returns claims: bugs, layout problems and UX suggestions. Claude reproduces every in-scope bug claim itself through the same restricted browser before calling it confirmed (otherwise it is reported as not confirmed, with what was tried), disposes every layout and UX claim with a reason, and reports. Nothing is fixed. **It is user-only:** only typing the command starts an exercise, and an exercise starts only after you answer its confirmation, which shows every command, address, data source, external dependency and disclosure. One model per exercise; the browser is headless unless you pass `--headed`. Windows only. The design is recorded in [ADR 0009](docs/adr/0009-exercise-on-a-disposable-target.md).

**Before the first exercise**, run `/ask-codex:setup` and ask it to prepare for exercises. It installs the pinned browser server (chrome-devtools-mcp 1.10.1) into `%LOCALAPPDATA%\ask-codex` with `npm install --ignore-scripts`, checks every installed file against a hash manifest committed with ask-codex, and checks node, Chrome (stable, 149 or later) and your codex-cli version. Then it starts the browser server once to check that it answers and lists its tools, and ends it again: it calls no browser tool, so Chrome itself normally does not start, and it leaves no process, directory or browser profile behind. Chrome first starts in each exercise's browser guard. `%LOCALAPPDATA%\ask-codex` holds only the browser server and the guard cache; deleting it removes both.

### Two modes

- **Copy mode** (default): the script copies your project into a newly created disposable target and starts the app from that copy with the install and start commands you confirm (Claude works them out from the project's files and shows package scripts and lifecycle hooks expanded; the script runs exactly the confirmed commands). The copy leaves out version-control metadata at any depth (`.git`, `.hg`, `.svn`, `.jj`), `.codex`, `.claude`, dependency directories (`node_modules`, `.venv`, `venv`, `__pycache__`, `.pnpm-store`), `.env*` files and secret-pattern files (`*.pem`, `*.key`, `*.pfx`, `*.p12`, `id_*`, `credentials*`). Links and junctions are skipped and listed, never followed or recreated; alternate data streams are not copied; by default a copy above 100,000 entries or 2 GiB fails. An env file reaches the copy only when you name it for that exercise, and the report's scope line lists it. The app uses the copy's own data (seed files, fixtures, test accounts created in the copy) unless you say, in the conversation for that exercise, to use your dev data; the report then says so on its second line.
- **Attach mode**: when you ask for it in the conversation for that exercise (for example "attach to my running dev servers"), the exercise uses the frontend and backend you already run. Nothing is copied, installed or started, and your servers are never started, stopped or signalled. Codex still works from a new, empty disposable directory. A project file, memory or an earlier exercise never selects attach mode, and it always counts as using your dev data. Before the confirmation the script shows the process that owns each attached port (its command line redacted); it refuses a port shared with another process, a server bound to every interface or to an IPv4-mapped address, the System process (http.sys), and owners on a closed forwarder list (`wslrelay.exe`, `com.docker.backend.exe`, `com.docker.proxy.exe`, `vpnkit.exe`, any `svchost.exe`). During the exercise it checks the owners every 2 seconds and stops the exercise on any change.

**Addresses.** Attach mode takes `127.0.0.1` only. `[::1]` and `localhost` are refused with a fixed sentence, "Attach mode takes 127.0.0.1 only: the allowlist of chrome-devtools-mcp does not support [::1], so bind your dev server to 127.0.0.1.", because chrome-devtools-mcp 1.10.1 cannot parse an unescaped `[::1]` URL pattern and the browser definition carries no backslashes. An entry with a scheme, such as `https://…` or `wss://…` (attach mode takes http `host:port` entries only), and the ports 80 and 443 are refused with messages of their own. Copy mode takes `127.0.0.1` and `localhost`; it also accepts `[::1]` in the request, but the guard then fails closed for the same reason, so no app starts. Bind dev servers to `127.0.0.1` (Vite `--host 127.0.0.1`, Next.js `-H 127.0.0.1`, Django `runserver 127.0.0.1:<port>`). The live guard passes were measured with `127.0.0.1` addresses.

**Target root.** The disposable target is created under a target root that comes only from you: your message, your global instructions or your memory. A project's own instructions can only suggest one, which Claude asks you to confirm. The script requires an existing directory on a local fixed drive, outside the project and not containing it, not in a cloud-sync folder such as OneDrive, and not under a directory that holds `.git` or `.codex`; the target itself must be new, and any existing path is refused.

### The boundary

- **Codex** runs with the same constants as a consultation: read-only shell, `--ephemeral`, apps and child agents off, no escalation (`approval_policy="never"`, `approvals_reviewer="user"`) and no execpolicy rules (`--ignore-rules`), with `-C` at the disposable target. Every other MCP server is disabled, whatever your ask-codex policy says, and the MCP guard requires exactly one enabled server: the exercise's browser server under a fresh name.
- **The browser server** is the pinned chrome-devtools-mcp 1.10.1, checked against the hash manifest before every use and launched with `node` directly (no `npx`, no shell) from a working directory of its own, with its own temporary directory and a Chrome profile that is created for the run, blocks downloads and is removed afterwards. Config-file discovery, usage statistics, update checks, CrUX lookups and JavaScript evaluation are off, and network headers are redacted. Codex gets 24 listed tools (pages and navigation, snapshots and screenshots, click, hover, fill, type, key presses, drag, dialogs, wait, resize, emulation, console and network listings, CSS styles, Lighthouse); `upload_file`, `evaluate_script`, heap snapshots, performance traces and any tool a later release adds are not exposed.
- **Per-tool approval.** Under `approval_policy="never"` Codex refuses MCP tools that need approval, so the exercise approves exactly the listed browser tools (`tools.<tool>.approval_mode="approve"`, server default `prompt`). These keys are command-line constants and are never set for `ask`, `review` or `discuss`. The browser tools' reach is bounded by the configuration below and checked by the guard, not by an approval prompt: Codex's browser actions are not reviewed one by one.
- **Network limit.** Chrome uses a proxy port the exercise holds, which closes every connection, with only the app's host:ports bypassed, plus the browser server's URL allowlist for those host:ports; WebRTC may use proxied UDP only. This is Chrome configuration plus an MCP allowlist, **not an OS sandbox**. The app itself runs with full network.
- **Files.** The browser's file-writing tools write only under `<target>/evidence` and the run's own temporary directory. Screenshots and logs are deleted with the target unless you ask, for that exercise, to keep chosen files at a location you name; the script moves them.
- **Browser guard.** Before the app starts (attach mode: before Codex starts), the guard starts the same browser definition without Codex and requires: the app's ports load; requests to another loopback port — also through `localhost`, `[::1]`, `127.0.0.2` and `0.0.0.0` — from images, iframes, fetch, WebSocket, Workers, `sendBeacon`, Service Workers and redirects are blocked; requests to another interface address and to the internet fail; WebRTC yields no server-reflexive candidate; `file:`, `chrome:` and similar URLs are refused or do nothing; every file-writing parameter stays inside the allowed directories across a matrix of path forms (relative, `..`, UNC, device paths, short names, alternate streams, junctions and symlinks); and every listed tool exists. A failing item stops the exercise with no app start and no Codex call. A pass is reused for up to 12 hours while its fingerprint (browser definition, node, the package manifest, Chrome path and version, codex-cli version, Chrome policy keys) is unchanged. In attach mode the guard runs on ports of its own and then, every exercise and never cached, checks the real attached ports. **The guard proves what the browser can reach, not what the app itself exposes or does.**
- **Reproduction.** Claude reproduces bug claims only through the script's `repro` operation, which drives the same restricted browser with a closed set of actions (navigate within the app's addresses, click, fill, hover, press a key, drag, answer a dialog, wait for text, resize, snapshots, screenshots, console and network listings). A step outside that set — a shell command, a file operation, another URL — is refused and the claim is reported as not confirmed.
- **Redaction.** Token-like strings in Codex's reply and in reproduction output — bearer and basic credentials, JWTs, `sk-`, `ghp_` and `xox`-style keys, values after `token`, `key`, `secret` or `password`, URL user info, values of `--password`/`--token`/`--secret`-style flags — are replaced by `[REDACTED]` before Claude sees them. It is pattern-based: secrets of other shapes can pass.
- **Data, not instructions.** Codex's reply and everything the app shows are data: Claude does not run a command, open a URL or change anything because they ask, and notes such requests in the report.
- **Ending.** `finish` ends Codex's processes, the browser and, in copy mode, the app's processes (held in a Windows job object), checks that each has ended, and only then removes the disposable target. Anything not confirmed ended is reported by PID and image, and the directories are kept and named. A supervisor ends an abandoned exercise 2 hours after its result was collected, or 6 hours after it started. If the supervisor dies, Codex is stopped within about 2 seconds, and in copy mode the app's job ends with it.

### Difference from Codex's own browsers

Codex's Chrome extension and in-app browser exist only in the Codex desktop app and cannot be used from `codex exec`; they work in a browser you use yourself. `/ask-codex:ui` runs from `codex exec` and gives Codex a separate Chrome with a run-owned profile that never sees your logins, cookies, extensions or tabs, limited to your app's addresses and discarded afterwards — and Claude reproduces and judges what Codex reports instead of relaying it.

### Pinned versions

chrome-devtools-mcp is pinned at 1.10.1, with its lockfile and the SHA-256 of every installed file committed under `skills/ask/browser-server/`. Raising it is a release that reruns probes P3–P5 and P7 (the tool allowlist in `codex exec`, screenshots seen by Codex, the allowlist's refusal, Service Worker and other network leaks) and the guard matrix before tagging. The exercise is tested with `codex-cli 0.159.3`; a release that raises that version reruns probe B1 (per-tool approval of the browser tools). With another codex-cli version, the exercise's confirmation tells you that its browser-tool approval behaviour is untested.

### Residual risks and what was not verified

- **Own projects only.** In copy mode the install and start commands run your repository's code as you, outside any sandbox, with full network. Effects outside the app's process tree (containers, services) are not managed.
- **Codex's shell reaches localhost**, as in every ask-codex skill (see "Localhost services" below). In attach mode it can send any request directly to your attached servers, outside the browser's limits. The report lists Codex's shell commands that name an attached host or port or an HTTP client; that list is a tripwire, not a control. `-C` does not hide your project from Codex's read-only shell.
- **The app's own development tools** reachable from the app's address (in-browser consoles, debuggers, open-in-editor or file-serving endpoints, including known dev-server file-serving flaws) can let Codex run code or read files as you, in both modes. This is disclosed in the confirmation and the report, not prevented or detected.
- **Browser actions are not reviewed one by one:** whatever the app does in response (mail, webhooks, payments, data changes) happens. Claude lists the external dependencies and integrations it finds and asks before the app starts.
- **Dev data and attach mode:** network request and response bodies, including your data, may reach OpenAI. In attach mode copy-mode exclusions do not apply, so whatever the dev server serves or shows (files, error pages, environment values, credentials you type) may reach OpenAI; its proxies and server-side requests reach anywhere with your credentials; reachability checks and Claude's reproduction also act on your real data; and your app may change your dev data and project files as a result of Codex's actions.
- **Attach-mode owners:** the exercise relies on your confirmation of which processes own the attached ports. Forwarders off the closed list (`ssh -L`, `kubectl port-forward`) are not detected, and an owner change can go unnoticed for up to the 2-second polling interval.
- **Supervisor death:** the proxy port is unheld for the seconds until Codex is stopped.
- **Run-owned temporary directory:** the browser server can write app-controlled bytes into it, and it also holds the isolated Chrome profile.
- **Approval visibility:** `tools.*.approval_mode` is not shown by `codex mcp get`, so the MCP guard cannot check it; the fresh server name and offline command-line tests cover it. Elicitation handling depends on the codex-cli version, and a codex-cli you upgrade yourself is untested until a release reruns probe B1.
- **Pins can be overridden** by administrator-level Codex configuration (see "Approval escalation") and by Chrome enterprise policy; the guard fingerprints the Chrome policy keys, so a policy change forces a new guard run.
- **Not verified:** DNS prefetch; headed mode (`--headed`); platforms other than Windows (every exercise operation refuses there).

## Comparison with the official Codex plugin

OpenAI's official Codex plugin has its own review commands. They are a different tool from `/ask-codex:review`:

| | `/codex:review` | `/codex:adversarial-review` | `/ask-codex:review` |
|---|---|---|---|
| Started by | you only | you only | you only |
| What Claude does with the output | returns it verbatim, no commentary | returns it verbatim, no commentary | judges every claim: adopt, reject or investigate, with a reason |
| Reviewer | Codex's built-in native reviewer | Codex, challenging the approach and design choices | Codex through `codex exec`, structured claims |
| Focus text | not supported | supported | supported, plus Claude's change intent as stance |
| Scope | working tree or branch (`--base <ref>`) | working tree or branch (`--base <ref>`) | working tree, `--base <ref>` or a commit range |
| Model and effort | `--model` is passed through (undocumented); no effort choice | `--model` is passed through (undocumented); no effort choice | aliases and effort, up to two models in parallel |
| MCP servers | not controlled by the command | not controlled by the command | disabled by default (ask-codex MCP policy); Codex shell read-only; child agents off |
| Foreground and background | `--wait`, `--background`, `/codex:status` | `--wait`, `--background`, `/codex:status` | foreground, with a check interval and stop reporting owned by the script |
| Runtime | plugin's shared companion script | plugin's shared companion script | `codex exec` called directly ([ADR 0001](docs/adr/0001-call-codex-exec-directly.md)) |

Use the official commands when you want Codex's native review exactly as it wrote it, or a background run you check later. Use `/ask-codex:review` when you want an independent second-opinion review that Claude weighs before anything is acted on, with your choice of model and effort and control over MCP servers. Both can run on the same change.

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

The UI exercise (1.4.0) is validated separately, on Windows: offline suites with stub Codex (`python evals/_harness/exercise_*_test.py`, plus the `ui-*` grader checks in the Node inventory); real-Claude evals of the skill in WSL with stub Codex and an eval platform fake; live checks without Codex of the browser guard (including negative controls that weaken one restriction each and must fail), reproduction and attach mode against a throwaway fixture app; and probe B1, which ran the browser tools through real Codex to measure per-tool approval. The release's live acceptance (2026-10-17, codex-cli 0.159.3, three real Codex calls) ran `/ask-codex:ui` in headless Claude Code sessions with this plugin loaded, against a throwaway frontend + backend fixture: one copy-mode exercise, one attach-mode exercise, and a copy-mode rerun. Every run found and reproduced the planted bug. The first two runs showed that Codex never saw its screenshots: a screenshot saved with `filePath` returns only a line of text. After the framing prompt was fixed to look without `filePath` and to save evidence with it, the copy-mode rerun returned the image to Codex for 8 screenshots. Every browser-tool call ran without an approval prompt, and Codex's shell commands were read-only. A screenshot written inside the evidence directory landed there, and one aimed outside it was refused. In attach mode, the user's servers survived with their identity unchanged. `config.toml` was unchanged, and no browser profile or exercise process was left behind. The evidence is under `.scratch/exercise-skills/evidence/c7-live/`. The interactive (non-headless) Claude Code flow and headed mode were not exercised.

See the [validation record](.scratch/script-owned-consultation/evidence/validation.md) for commands, reports, regression history and remaining acceptance gaps. Historical evals for the previous implementation are not proof of current behavior. macOS is outside the current acceptance scope.

## Known risks and limitations

- **MCP configuration race (unresolved):** preflight and `codex exec` load configuration separately. A new server added after the guard has no disabling override; an allowed server's definition can also change before execution. The guard does not provide an atomic configuration snapshot. Keep Codex settings and plugin configuration unchanged throughout preparation and execution; this operational precaution is not enforcement against concurrent or malicious changes. See the [investigation](docs/mcp-configuration-race.md).
- **MCP access:** allowed tools execute outside the shell sandbox. Prompt instructions cannot enforce read-only behavior inside those tools, and an allowed server can itself start agents (for example `codex mcp-server`), which the child-agent switches do not cover. Read-only shell execution also does not itself constrain access to only the files relevant to your question.
- **Request provenance:** consultation and confirmation require your own request under the skill's rules, but that rule depends on Claude following instructions. Earlier tests exposed a file-originated request before a request check was added; the limited subsequent checks do not prove immunity to prompt injection.
- **Process snapshots:** tracking covers observed descendants, including captured detached children, and checks identities before individual signals. A child that detaches and is reparented before observation can escape discovery. If a PID/group is reused and its replacement leader exits before observation, the remaining group may be mistaken for the original group and signalled. The plugin does not provide kernel-enforced process ownership.
- **Unconfirmed stops:** processes may remain alive when enumeration or identity checks are unavailable, including restricted Windows process-query permissions. Keep the reported diagnostics; root exit or a quiet log alone does not prove termination.
- **Retained content:** unresolved stops retain files a process may still need. Error logs may contain project content. Diagnostic cleanup requires an explicit request and confirmed termination; there is no automatic expiry.
- **Platform and configuration:** a historical Windows RAM-disk test failed with `os error 1`; that is not a diagnosis for every OS error. Persistently trusted project definitions have not been validated end to end with the real Codex CLI. When no session model is selected, an external change to the configured model can affect the next consultation.
- **Child agents (fixed in 1.3.2; affected 1.0.0–1.3.1):** Codex can spawn child agents (on by default, MultiAgentV2 for most current models). A child's role file — for example `~/.codex/agents/*.toml`, which codex-feather installs, or a trusted project's `.codex/agents` — sets its own sandbox, model and MCP servers, and the role's sandbox overrides the consultation's `-s read-only`. Up to 1.3.1 a consultation could therefore spawn a `workspace-write` child that wrote files in your project, used MCP servers the ask-codex policy never saw, and ran on the role's model; the event stream shows at most a `collab_tool_call` "wait" item, not the spawn or the child's writes. Since 1.3.2 every consultation passes `-c agents.enabled=false -c features.multi_agent_v2.enabled=false`. Verified on codex-cli 0.159.3 (Windows) with live probes: default configuration with a v2 and a v1 model, and a trusted project whose `.codex/config.toml` enables agents, MultiAgentV2, fan-out and multi_agent — no spawn tool, no write. Not verified: your own Codex config enabling these (the command line takes precedence over config files), older CLIs, WSL. `--disable multi_agent` alone does not stop MultiAgentV2. If you used `review` or `discuss` on untrusted content with 1.3.1 or earlier and have write-capable roles installed, check `git status` in those projects; update the plugin (manual copies: copy the skills again).
- **Approval escalation (fixed in 1.3.3; affected 1.0.0–1.3.2):** `codex exec` normally refuses every approval request in headless mode, but drops that when your configuration resolves `approvals_reviewer` to `auto_review`; approval requests then go to Codex's automatic reviewer. Up to 1.3.2 a consultation could therefore ask to run a command outside the read-only sandbox and have it approved: on codex-cli 0.159.3 (Windows) a probe consultation wrote a file this way. A trusted project's `.codex/config.toml` can set the same keys. Since 1.3.3 every consultation passes `-c approval_policy="never" -c approvals_reviewer="user"`, which take precedence over your config and project config (and, by source reading, over profiles, which were not probed). Verified on codex-cli 0.159.3 (Windows) with live probes: your config with `auto_review`; a trusted project setting `auto_review` with `on-request` or with the granular policy with all five prompt kinds enabled, plus `sandbox_mode = "workspace-write"`; and an untrusted project — no escalation was requested, nothing was written, and `-s read-only` held against the project's `sandbox_mode` (the project's `default_permissions` is ignored by Codex when `sandbox_mode` or `-s` is present, so it was not tested on its own). Limits: in every live run the model declined to send an escalation request once told the policy is `never`, so Codex's runtime refusal of such a request was not exercised live, and the result of a permissions request in one run is known only from the model's own report; the `approvals_reviewer` pin is a second layer that was not probed on its own. Not covered: administrator layers (a legacy managed config, or `requirements.toml` that disallows `never`) can override or replace these values. If you used a consultation on 1.3.2 or earlier with `auto_review` set in your config or in a trusted project's config, an approved command could have written anywhere your account can write, not only in the project: check `git status` in those projects and any other files you are concerned about; update the plugin.
- **Execpolicy rules (since 1.3.3):** an `allow` rule in an execpolicy `.rules` file (yours under `~/.codex/rules/`, which Codex writes when you choose "don't ask again", or a trusted project's `.codex/rules/`) can let a matching command run outside the sandbox regardless of the approval policy. This is inferred from the Codex source and was not probed. Since 1.3.3 consultations pass `--ignore-rules`, so your and the project's `.rules` files are not loaded — your own `forbidden` and `prompt` rules do not apply in consultations either; commands still run inside the read-only sandbox. Not covered: system-level rules (under `%ProgramData%\OpenAI\Codex\` on Windows), administrator `prefix_rules` and rules a plugin brings are presumably still loaded (static reading of codex-cli 0.159.3; not probed).
- **Localhost services:** on Windows the read-only sandbox blocks outbound network but not loopback (measured on codex-cli 0.159.3, elevated sandbox). Codex's network proxy settings block proxied requests to loopback, but a command that bypasses the proxy still connects. In every ask-codex skill — `ask`, `review`, `discuss` and the `ui` exercise — Codex's shell commands can therefore send requests to any service listening on 127.0.0.1 on your machine, such as a development database's admin interface. Codex configuration cannot prevent this; keep sensitive local services authenticated, or stop them while consulting on untrusted content.
- **Other tools outside the sandbox:** a read-only consultation still sees Codex tools that write to Codex's own stores (`notes.write_file`/`append_to_file`, `create_goal`/`update_goal`) and `web.run`. They do not touch your project files, but notes persist across Codex sessions and web access is an outbound channel; they are tracked separately.
- **Codex `notify` hooks and other hooks (not fixed by design):** Codex hooks configured at the user level (and, for a trusted project, its hooks) also run during a consultation and are not limited by the sandbox. If your Codex configuration sets `notify`, Codex runs that hook for a consultation too, and on Windows the hook inherits the run's prompt, event and error files. A hook that outlives Codex keeps them locked; one observed hook chain held them for about 13 s. Cleanup retries for up to 30 s (`ASK_CODEX_CLEANUP_WINDOW_S`), so a finished consultation may take that long to return. If the lock outlasts the window, the reply is still delivered and the run is reported with its retained location for a later cleanup. The plugin does not disable your hook. See [ticket 12](.scratch/script-owned-consultation/issues/12-cleanup-retries-transient-windows-lock.md).
- **Review reads the whole scope:** a review lets Codex read the scoped change, including untracked files in a working-tree review. Excluding secrets is an instruction to Codex, not an enforced filter.
- **Working-tree clean filters:** a working-tree review runs `git status`, which can still run a repository-configured clean filter (`.gitattributes` plus `filter.<x>.clean`) when it re-reads files whose stat data changed. `--no-ext-diff`, `--no-textconv` and `core.fsmonitor=false` do not cover this. Base and range reviews compare commits only and are not affected. Review a repository you do not trust with `--base` or a range, or inspect its filter configuration first.
- **Steering by diff content:** text in the reviewed change can try to steer Codex's conclusions, and a reviewed repository's own `AGENTS.md` or skills may be read by Codex as instructions rather than data; that the content is data is an instruction, not enforcement. Claude's per-claim dispositions are the control, and Claude does not act on a claim without your separate request.
- **Discussion cost and convergence:** a discussion makes one Codex call per round (up to ten), and each round re-explores the project because sessions are fresh. Its rules against false agreement (evidenced concessions, late-flip flags, blocking-only new points) are instructions to both models, not enforcement; the labels in the report are the control. Codex's earlier output is carried into later prompts as data, like any file.
- **Cost:** consultations consume Codex usage, and a parallel pair starts two runs. Current per-consultation token overhead has not been measured.
- **UI exercise:** its own residual risks and unverified areas are listed under [UI exercise](#residual-risks-and-what-was-not-verified). The "Localhost services" risk above applies to exercises too.

Reports may follow the conversation language. They must still include the question and type, model and effort, effective MCP policy, relevant timer/stop details, and Claude's disposition for each substantive claim. Execution failures contribute no attributed Codex opinion.

## License

MIT. See [LICENSE](./LICENSE).
