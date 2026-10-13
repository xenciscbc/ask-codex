# Spec: ask-codex UI exercise skill (`/ask-codex:ui`)

Status: ready-for-agent

Blocked by: None — `.scratch/approval-boundary/issues/01` was released in 1.3.3 (user decision Q33, 2026-10-13; tag v1.3.3 on 1ca7a0f). The UI exercise command line pins the same constants as consultations since 1.3.3: `approval_policy="never"`, `approvals_reviewer="user"` and `--ignore-rules` (ADR 0010).

Vocabulary follows `CONTEXT.md`: **演練** (exercise) and **可丟棄目標** (disposable target), added 2026-10-13 during the grilling session; **諮詢**, **論點**, **處置**, **停止**, **殘留行程**, **MCP 政策**, **MCP 事前檢查**, **模型簡稱**, **模型指定**, **諮詢 effort** as already defined. Decisions respect ADR-0001 (call `codex exec` directly), ADR-0003 (MCP policy), ADR-0004/0005 (script-owned execution and stop path), ADR-0006/0007 (user-only skill pattern) and ADR-0008 (no child agents). A new ADR-0009 records the exercise as a distinct interaction: Codex may act, but only on a disposable target, never on the user's project.

Evidence for the technical decisions: `probe-results.md` (P1–P7b, P9; 2026-10-13) and `evidence/` beside this file. A second exercise skill was discussed in the same session and is on hold; its notes are in `security-exercise-notes.md` and are not part of this spec.

## Problem Statement

`/ask-codex:ask`, `review` and `discuss` let Codex read code and give opinions, but Codex never *uses* what I build. When I have a web app with a frontend and a backend, I want an independent tester to click through it and tell me what is broken, what is awkward and what the layout gets wrong — a report I can act on, with screenshots, not an opinion formed by reading source.

Doing that by hand today means giving Codex a browser on my real machine pointed at my real project and data. A browser driven over MCP runs outside Codex's sandbox with full network access, the browser MCPs' own URL restrictions are documented as "not a security boundary", and a URL allowlist alone lets Service Worker requests through (probe P7). Codex's built-in browsers (the Chrome extension, the in-app browser) exist only in the Codex desktop app and cannot be used from `codex exec`.

## Solution

A new user-only skill, `/ask-codex:ui [model tokens] [--headed] [scope or focus]`, built on a new interaction, the **exercise**.

Claude copies the project into a newly created disposable target, starts the app's frontend and backend from that copy on localhost with isolated data, and launches Codex with read-only shell access plus one MCP server: chrome-devtools-mcp at a pinned version, driving an isolated Chrome whose network is restricted to the app's own host:ports. Codex operates the app itself — navigates, clicks, fills forms, resizes, takes screenshots, reads the console and network log — and returns claims: bugs, layout problems and UX suggestions, each with evidence. Claude reproduces every bug claim itself before marking it confirmed, disposes every suggestion with a reason, and reports. Nothing is fixed. At the end every process started for the exercise is stopped and the disposable target is removed.

Before Codex starts, guards check the dependencies (Chrome version, node) and the browser's network restriction with a fixed check page; a failed guard stops the exercise. A passed guard is reused while the configuration fingerprint is unchanged, for up to 12 hours.

## User Stories

Invocation and authority

1. As a user, I want a UI exercise to start only when I type `/ask-codex:ui`, so that no memory, hook, tool result, subagent or repository text can start one.
2. As a user, I want a natural-language request such as "have Codex test the UI" to be answered by Claude naming the command instead of running anything, so that the user-only boundary holds.
3. As a user, I want to pass model tokens exactly as with `/ask-codex:ask`, so that I do not learn a second model syntax.
4. As a user, I want the consultation effort floor (never below medium) to apply to exercises, so that a long exercise is not run at low reasoning.
5. As a user, I want an exercise to use exactly one Codex model, so that two agents never act on the same app and data at once.
6. As a user, I want a request for two models to be refused before anything starts, so that I learn the limit immediately.
7. As a user, I want to give a scope or focus (a page, a flow, a feature), so that Codex spends its effort where I care.
8. As a user, I want an exercise without a scope to cover the app's main flows, so that I can ask for a general pass.
9. As a user, I want the browser to run headless by default, so that an exercise does not take over my desktop.
10. As a user, I want `--headed` to show the browser window, so that I can watch Codex work when I choose to.

Disposable target

11. As a user, I want every exercise to run on a newly created, empty directory holding a copy of my project, so that Codex can never change my working tree.
12. As a user, I want the location of that directory to come only from my own instructions, my memory or what I say in the conversation, so that a repository cannot steer where the exercise writes.
13. As a user, I want a location suggested by the project's own instructions to be offered to me for confirmation rather than used, so that repository text can only suggest.
14. As a user, I want Claude to ask me for a location when no user-level source names one, so that nothing is guessed.
15. As a user, I want the script to refuse an existing directory as the target, so that a wrong location can never lead to writing into or deleting my files.
16. As a user, I want removal at the end to delete only the directory the script created, so that cleanup can never reach anything else.
17. As a user, I want the copy to leave out version-control metadata and other content the app does not need to run, so that the exercise cannot reach my repository history.
18. As a user, I want the exercise to fail clearly when the copy cannot be made (for example on a volume where it fails), so that it never falls back to my working tree.

Starting the app

19. As a user, I want Claude to work out how to start the frontend and backend from the copy, so that I do not write start scripts for each project.
20. As a user, I want to be able to state start commands, ports or environment myself, so that Claude does not guess wrong on unusual projects.
21. As a user, I want Claude to prepare isolated data for the copy (a seeded database copy, test accounts), so that the exercise never writes my development data.
22. As a user, I want Claude to list every external dependency of the backend (remote database, third-party API, message broker) and ask before starting, so that I decide whether the exercise may reach them.
23. As a user, I want to be able to say, for one exercise, "use the dev data", so that I can test against realistic data when I choose to.
24. As a user, I want that choice to count only when I say it in the conversation for this exercise, so that a project file or memory cannot switch an exercise onto my real data.
25. As a user, I want the report to say at the top that the exercise used dev data and may have written outside the disposable target, so that I know what may have changed.
26. As a user, I want Claude to confirm the app answers on its ports before Codex starts, so that Codex does not spend its run on a dead app.
27. As a user, I want a failure to start the app reported with its output and no Codex call made, so that I can fix the setup without spending quota.

The browser Codex gets

28. As a user, I want Codex to get its own isolated Chrome profile that is discarded afterwards, so that it never sees my logins, cookies, extensions or tabs.
29. As a user, I want the browser's network limited to the app's own host:ports, so that nothing the app or Codex does in the page reaches the internet or my other local services.
30. As a user, I want that limit enforced by two independent layers (Chrome's proxy settings and the MCP URL allowlist), so that one layer's gap (for example Service Workers, P7) is covered by the other.
31. As a user, I want tools that run arbitrary JavaScript, upload local files or write large files to be unavailable to Codex, so that the browser is used to test the app and nothing else.
32. As a user, I want only an explicit list of browser tools exposed to Codex, so that tools added by a future MCP release are not exposed automatically.
33. As a user, I want the MCP server pinned to a known version, so that an upstream change cannot silently weaken the restrictions.
34. As a user, I want the MCP server's telemetry, external performance lookups and project config discovery off, so that the exercise sends nothing to third parties and the project cannot reconfigure the browser.
35. As a user, I want all my other MCP servers disabled during an exercise as in a consultation, so that the exercise has exactly one tool server.

What Codex does

36. As a user, I want Codex's shell to stay read-only, so that Codex tests through the browser and never edits the copy or anything else.
37. As a user, I want Codex unable to request escalated permissions, so that no approval path widens the exercise (approval-boundary/01).
38. As a user, I want child agents off as in every consultation, so that no role file widens the sandbox (ADR 0008).
39. As a user, I want Codex told to discover its browser tools first, so that deferred MCP tools do not make it believe it has none (P3).
40. As a user, I want Codex to look at screenshots, not only the DOM snapshot, so that visual problems are actually seen (P4).
41. As a user, I want Codex to check layout at several viewport sizes including a phone size, so that responsive problems are found.
42. As a user, I want Codex to read the browser console and failed network requests, so that hidden errors behind a working-looking page are reported.
43. As a user, I want Codex to stay inside my scope and list anything it notices outside it as "out of scope, not tested", so that the exercise does not wander.

Claims, verification and report

44. As a user, I want each claim classified as a bug, a layout problem or a UX suggestion, so that I can triage the report.
45. As a user, I want each bug claim to come with exact reproduction steps, the expected and the actual result and a screenshot, so that it can be reproduced.
46. As a user, I want Claude to reproduce every bug claim itself in the same disposable target before calling it confirmed, so that a misread or mistyped observation (P2b) never reaches me as fact.
47. As a user, I want a bug Claude cannot reproduce marked "not confirmed" with what Claude tried, so that nothing is silently dropped or silently trusted.
48. As a user, I want Claude to dispose every layout problem and UX suggestion as adopt, reject or investigate with a reason, so that I get Claude's judgement, not a relay of Codex.
49. As a user, I want the report to start with the scope line: app, ports, scope, model, headless or headed, data source, and any guard reused from cache, so that I know exactly what was exercised.
50. As a user, I want the report to list out-of-scope observations separately, so that I can decide whether to run another exercise.
51. As a user, I want "no claims" never to be presented as approval of the UI, so that an empty report is not misread.
52. As a user, I want the exercise never to fix anything, so that changes stay my decision and a separate step.

Evidence

53. As a user, I want screenshots and logs deleted with the disposable target by default, so that nothing accumulates in my project.
54. As a user, I want to ask for chosen evidence to be kept and moved to a location I name before the target is removed, so that I can attach it to a ticket.

Guards

55. As a user, I want the exercise to check that Chrome is version 149 or later and node is available, and to stop with a clear message otherwise, so that a missing dependency is not discovered mid-run.
56. As a user, I want a browser guard before each exercise that opens a fixed check page with the exact browser configuration, so that a broken restriction stops the exercise before Codex starts.
57. As a user, I want the browser guard to prove both that the app's ports are reachable and that ordinary requests, Service Worker requests, WebSocket, WebRTC, other local ports and the internet are blocked, so that every path measured in P7 is re-checked.
58. As a user, I want a passed guard reused while the fingerprint (Chrome version, MCP version, full launch arguments including ports) is unchanged and for at most 12 hours, so that I do not wait for the same check repeatedly.
59. As a user, I want any change in that fingerprint to force a new guard run, so that a Chrome update or a different app is never covered by an old result.
60. As a user, I want the guard to run without calling Codex, so that it costs no quota.
61. As a user, I want `/ask-codex:setup` to check the exercise dependencies too, so that I can prepare a machine in advance.

Stop and cleanup

62. As a user, I want the existing check interval, liveness check and stop rules to apply to exercises, so that a long exercise behaves like a long consultation.
63. As a user, I want stopping an exercise to end the Codex process tree, the app's processes and the MCP-launched Chrome, so that no orphaned run keeps using quota, ports or memory.
64. As a user, I want the stop report to say whether each of those was confirmed ended, so that "called stop" is never presented as "stopped".
65. As a user, I want the disposable target removed after a normal finish, a failure or a stop, and its location reported if removal fails, so that I can clean up by hand.
66. As a user, I want an exercise that failed or was stopped not to be retried automatically, so that quota is spent only when I decide.

Documentation

67. As a user, I want the README to state plainly that the browser's network limit is Chrome configuration plus an MCP allowlist, not an OS sandbox, so that I do not over-trust it.
68. As a user, I want the README to state that Codex's shell can reach every localhost service on the machine in all ask-codex skills, so that I know the remaining risk (P2, P8c).
69. As a user, I want the README to list what was not verified (DNS prefetch, headed mode), so that the limits are honest.
70. As a user, I want both READMEs (English and Traditional Chinese) to describe the skill, its boundary and its difference from Codex's own browsers, so that I can choose the right tool.

## Implementation Decisions

- **New interaction, not a wider consultation.** The exercise is a separate interaction (CONTEXT.md, ADR-0009, status proposed). `ask`, `review` and `discuss` keep their command lines unchanged apart from approval-boundary/01.
- **One execution boundary.** The exercise extends the script-owned execution boundary of ADR-0005: the same `consult.py` CLI gains request fields and subcommands rather than a second script. The skill's prompt files live with the new skill; the scripts stay under the `ask` skill as `review` and `discuss` already do.
- **Request fields (exercise).** Interaction type `exercise` with kind `ui`; disposable target root (a user-confirmed parent location); app host:ports; headed flag; scope text; one model. Validation refuses: more than one model, a target that already exists, a target root not confirmed by the user, no ports, ports outside loopback.
- **Disposable target lifecycle** as CLI subcommands: create (new empty directory under the confirmed root, copy of the project excluding version-control metadata, refuse on any existing path), and remove (delete only the directory recorded at creation, identity-checked). The run record keeps the created path so that stop and cleanup remove exactly it.
- **Command line (constants, not part of overrides or the prepared summary, as in ADR-0008):** `codex exec -s read-only --ephemeral --skip-git-repo-check --json -C <disposable target>`, model and effort as for consultations, the MCP policy overrides with every other server disabled, `--disable apps`, `-c agents.enabled=false`, `-c features.multi_agent_v2.enabled=false`, `-c approval_policy="never"`, `-c approvals_reviewer="user"`, `--ignore-rules` (ADR 0010), and the browser server definition below.
- **Browser server definition** via `-c mcp_servers.<name>.*`: command `cmd /c npx -y chrome-devtools-mcp@<pinned>` (P3 showed this starts under Codex's default MCP environment); arguments `--isolated`, `--headless` unless headed, `--no-javascript-evaluation`, `--no-usage-statistics`, `--no-performance-crux`, `--viewport`, `--allowedUrlPattern` for each app host:port, `--proxyServer` pointing at a closed local port, `--chromeArg=--proxy-bypass-list=<-loopback>;<each app host:port>` and `--chromeArg=--force-webrtc-ip-handling-policy=disable_non_proxied_udp`; env `CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY` and `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS`; `startup_timeout_sec` raised. The `<` and `>` in the bypass list must survive the launcher: P7 showed `cmd /c` treats them as redirection, so the definition must launch in a way that passes them literally (to be settled by the first slice and proved by the browser guard).
- **Tool allowlist** via `enabled_tools` (P3 proved it effective in `exec`): `navigate_page`, `new_page`, `list_pages`, `select_page`, `close_page`, `take_screenshot`, `take_snapshot`, `click`, `hover`, `fill`, `fill_form`, `type_text`, `press_key`, `drag`, `handle_dialog`, `wait_for`, `resize_page`, `emulate`, `list_console_messages`, `get_console_message`, `list_network_requests`, `get_network_request`, `get_css_styles`, `lighthouse_audit`. Not exposed: `upload_file`, `take_heapsnapshot`, `performance_*`, and anything a later release adds.
- **MCP guard.** The existing preflight MCP guard must expect exactly the browser server as the one enabled server for an exercise and abort otherwise.
- **Guards as a CLI subcommand.** Dependency check (Chrome stable version from the system, ≥149; node present). Browser guard: start the same MCP launch configuration directly over stdio (no Codex), open a fixed check page served on one of the exercise ports' loopback host by the script, and require: page loads; ordinary subresource, fetch, WebSocket, Worker, sendBeacon, Service Worker requests to another loopback port are blocked; requests to an external host from the page and from a Service Worker fail; WebRTC yields no server-reflexive candidate. The probe page and server of P7 (`probe-leaks.py`) are the prior art.
- **Guard cache.** Key = fingerprint of Chrome executable version, MCP package version and the full launch argument list; value = pass time. Reused within 12 hours when the fingerprint matches; otherwise rerun. Stored with the user-level run state, never in the project.
- **Framing prompt** for the UI exercise: discover tools first; stay in scope; take screenshots and judge visually; several viewports including phone; read console and network failures; out-of-scope observations listed separately; reply in a UI-exercise reply schema.
- **Reply schema** (new, selectable like `discussion.schema.json`): claims with `category` (bug, layout, ux), `statement`, `steps`, `expected`, `actual`, `viewport`, `evidence` (screenshot reference or console or network entry), `confidence`, `in_scope`; plus `out_of_scope` observations and `coverage` (pages and flows visited).
- **Claude's side (SKILL.md).** Resolve the target root from user-level sources only, else ask; work out and confirm app start commands, data isolation and external dependencies (ask before starting); dev data only on an explicit statement in the conversation for this exercise; start the app from the copy; run guards; run the exercise; reproduce each bug claim in the browser before marking it confirmed; dispose each claim; write the report with the scope line first; stop everything and remove the target.
- **Stop and cleanup.** The exercise run record lists the app process trees and the target directory; `stop` and `cleanup` end the Codex tree, the app trees and the MCP-launched Chrome, then remove the target, reusing the ADR-0004 stop path.
- **Setup.** `/ask-codex:setup` gains a dependency check for exercises (Chrome version, node, ability to start the pinned MCP).
- **Pinned version policy.** Raising the MCP version is a release: rerun the P3–P5 and P7 probes before tagging.
- **Version.** Minor release after 1.3.3 (new skill).

## Testing Decisions

A good test exercises external behavior through the highest existing seam and never asserts on internal helpers: what reaches Codex's command line, what is created and removed on disk, what the CLI refuses, what the skill tells the user.

- **Seam 1 — `consult.py` CLI with the Codex stub (main seam).** Prior art: `evals/_harness/consultation_test.py` (`BASELINE_ARGV`, run lifecycle tests) and the stub in `evals/_harness/stub/`. Tests: the exercise command line carries every constant (read-only, no escalation, child agents off, apps off, only the browser server, the exact `enabled_tools`, proxy, bypass list with exactly the app ports, WebRTC policy, allowlist patterns, `-C` at the disposable target); `ask`, `review`, `discuss` command lines unchanged by the exercise work; validation refusals (two models, existing target, unconfirmed root, no ports, non-loopback port); target creation copies without version-control metadata and refuses existing paths; removal deletes only the recorded directory; stop ends app trees and the target is removed after finish, failure and stop; the MCP guard refuses any second enabled server.
- **Seam 2 — guards.** Offline, through the CLI with the guard command replaced by a fake via environment (the same substitution style as the Codex stub on PATH): a failed guard means no Codex launch; cache hit on an identical fingerprint within 12 hours; rerun on any fingerprint change or expiry. The real browser and network judgement is tested live only (P7 is the prior art).
- **Seam 3 — Claude eval harness for the skill.** Prior art: `evals/discuss-not-model-invocable`, the review and discuss grader tests, `evals/_harness/run-evals.sh` via WSL. Cases: not model-invocable; natural-language request answered with the command only; project-suggested target location asked, not used; dev data only with an explicit statement; report starts with the scope line and separates out-of-scope items; unreproduced bug marked not confirmed; no fix offered as done. Deterministic graders over final messages preferred to LLM judges (memory: eval grader lessons).
- **Seam 4 — live acceptance before release.** One real UI exercise against a throwaway web app with a frontend and a backend, with `config.toml` hash and PID baselines (memory: live testing on this machine); confirm screenshots are seen, guards pass, the target and all processes are gone afterwards.

## Out of Scope

- The security exercise skill (on hold; `security-exercise-notes.md`).
- Non-web interfaces: desktop apps, mobile, TUI.
- Codex's own browsers (Chrome extension, in-app browser): desktop-app only, not usable from `codex exec`.
- Operating my everyday Chrome profile or any signed-in session.
- Targets other than localhost services started from the disposable target.
- Parallel exercises or more than one model.
- Fixing anything the exercise finds.
- Blocking Codex's shell from other localhost services (not possible with Codex configuration on this machine, P8c; README note only).
- An OS-level browser sandbox (WFP rules, containers, WSL).

## Further Notes

- Measured on Windows 11, codex-cli 0.159.3 (elevated sandbox), Chrome 154, node 24, chrome-devtools-mcp 1.10.1. Other platforms are untested.
- P2b showed Codex misreporting a token it had read correctly; this is why Claude reproduces bug claims.
- approval-boundary/01 landed in 1.3.3 (ADR 0010); the exercise relies on the same pinned approval policy, reviewer and ignored rules.

## Decision log (grilling 2026-10-13, user-confirmed)

| # | Decision |
|---|---|
| Q1, Q7 | Codex operates the browser itself (chrome-devtools-mcp); Claude-driven screenshots rejected |
| Q2 | Web only |
| Q5, Q12, Q31 | User-only skill `/ask-codex:ui [model] [--headed] [scope]`, separate from the on-hold security skill |
| Q6 | New interaction 演練 (exercise); consultations stay read-only |
| Q8, Q10 | Disposable target under a user-level location; project instructions only suggest; new empty directory only |
| Q11, Q14 | App started from the copy with isolated data; external dependencies asked; dev data only on explicit per-exercise statement, flagged in the report |
| Q13 | Bug claims reproduced by Claude; layout and UX claims disposed with reasons and screenshots |
| Q15 | Report only, no fixes |
| Q16 | Evidence deleted with the target unless the user asks to keep it at a named location |
| Q17 | Model rules as `ask`; one model |
| Q18 | Out-of-scope observations listed, not tested |
| Q21 | Headless by default, headed on request |
| Q22 | Tool allowlist as listed above |
| Q23, Q23' | Browser guard each exercise; result reused by fingerprint for up to 12 hours |
| Q25 | Dependency checks; pinned MCP version; reprobe on upgrade; setup check |
| Q26–Q28 | Service Worker gap found and closed with proxy + bypass list; WebRTC blocked; README lists what remains |
| Q29' | Shell loopback reach: README note only |
| Q32, Q33 | approval_policy pinned; approval-boundary/01 released first |
| Assumption (stated in the summary) | Check interval, liveness, stop and orphaned-run rules reused; stop also ends app processes and Chrome and removes the target |
