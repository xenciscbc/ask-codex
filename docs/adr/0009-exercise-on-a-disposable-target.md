---
status: accepted
---

# Exercises: Codex may act, but only on a disposable target

A UI review needs Codex to operate a running app, which a read-only consultation cannot do. We add a second kind of interaction, the exercise (演練, `CONTEXT.md`), started only by a user-typed command (first: `/ask-codex:ui`). In an exercise Codex may act — drive an isolated, network-restricted Chrome against the app — but only on a disposable target (可丟棄目標): a newly created directory under a location the user confirmed, removed at the end. In copy mode (副本模式) it holds a copy of the project and the app is started from that copy on localhost; in attach mode (接上模式), chosen by the user for one exercise, it is an empty directory and the browser uses the frontend and backend the user already runs, which the exercise never starts, stops or signals. Codex's shell stays read-only, it can never request escalation, and Codex and its browser never write to the user's project: they write nothing outside the disposable target and the run's own directories apart from Codex's own state (`CODEX_HOME`, as in every consultation). `ask`, `review` and `discuss` keep their read-only guarantee unchanged; the exercise is a separate guarantee, not a widened consultation. The result is still claims that Claude judges; bug claims count only after Claude reproduces them through the same restricted browser.

"Never writes to" replaces the earlier "never touches": Codex's read-only shell can still read the project and every file the user can read (`-C` points Codex at the disposable target but does not hide the project from the shell), and in attach mode the app the user runs reads and writes the project by itself.

## Recorded exceptions

The exercise departs from earlier decisions in these places, each on purpose:

- **Per-tool approval of the browser tools (against ADR 0010's refusal).** Consultations refuse every approval request (`approval_policy="never"`). Under that policy the browser server's tools are refused too (probe B1), so the exercise approves exactly its allowlisted browser tools with `mcp_servers.<server>.tools.<tool>.approval_mode="approve"` and pins the server's default to `prompt`. These keys are command-line constants generated from the same fixed tool list; they never appear in the MCP policy overrides, the prepared summary or `plan.json`, and never on `ask`, `review` or `discuss`. No shell escalation is approved: the shell keeps `approval_policy="never"`, `approvals_reviewer="user"` and `--ignore-rules`. The boundary of the approved tools is therefore the browser server's own configuration (allowlist, proxy, file-system root) and the guard that checks it, not an approval prompt; Codex's browser actions are not reviewed one by one.
- **Every other MCP server disabled (against ADR 0003's allowlist).** An exercise disables every MCP server except its own browser server, whatever the user's ask-codex policy, allowlist or minimal-deny mode says, and the MCP guard requires exactly that one enabled server.
- **Fixed disclosure sentences (against ADR 0005's report-language guidance).** ADR 0005 lets reports follow the conversation language without fixed sentences. An exercise's disclosures (plan I16) are fixed sentences with an English and a Traditional Chinese version; the skill uses the version of the conversation's language, and any other language gets the English one. The evals grade the exact sentences.
- **Attach mode: effects through the app.** In attach mode the user's own app may change the user's dev data and project files as a result of Codex's actions. Codex and its browser still write nothing there themselves; what the app does in response is the user's choice and is disclosed in the confirmation and the report.
- **Both modes: the app's own development tools.** In-browser consoles, open-in-editor endpoints and file-serving flaws reachable from the app's address can let Codex run code or read files as the user. They are disclosed (confirmation, report, README), not prevented or detected.
- **Windows only (against ADR 0005's Windows and Linux targets).** The exercise's mechanisms (job objects, the listener table, the platform layer) are Windows-only; every exercise operation refuses on other hosts.

## Considered Options

- **Widen the consultation** so that every skill may act: rejected — it would weaken the guarantee the three existing skills make, for a capability only one use needs.
- **Move UI testing out of ask-codex** into another plugin: rejected — it would duplicate the script-owned execution boundary (ADR-0005), the MCP policy (ADR-0003) and the stop path (ADR-0004).
- **Claude drives the browser and Codex directs it from screenshots**: rejected by the user — Codex's own exploration is the point of the exercise.
- **Codex's own browsers** (Chrome extension, in-app browser): only available in the Codex desktop app, not from `codex exec`.

## Consequences

- The browser runs outside Codex's sandbox (MCP servers always do, ADR-0003). Its network is limited by Chrome configuration (a closed proxy with only the app's host:ports bypassed) plus the MCP URL allowlist; neither is an OS sandbox, and the URL allowlist alone let Service Worker requests through (probe P7, `.scratch/exercise-skills/probe-results.md`). A browser guard re-checks these paths before an exercise. The guard proves what the browser can reach, not what the app itself exposes or does.
- Where the disposable target lives is decided only by user-level sources (the user's instructions, memory or conversation); project instructions can only suggest, because the target is where the exercise writes and what it deletes.
- Codex's shell can reach every localhost port on the machine even with network off (P2, P8c); Codex configuration cannot prevent it on Windows. This is documented, not solved, and applies to all skills; in attach mode it includes the attached servers, and the report lists Codex's shell commands that name them (a tripwire, not a control).
- In copy mode the app's install and start commands run the repository's code as the user, outside any sandbox, with full network. Exercises are for the user's own projects only.
- The browser server is pinned (chrome-devtools-mcp 1.10.1, verified against a committed hash manifest before every use). Raising it is a release that reruns probes P3–P5 and P7 and the guard matrix; a release that raises the tested codex-cli version reruns probe B1.
