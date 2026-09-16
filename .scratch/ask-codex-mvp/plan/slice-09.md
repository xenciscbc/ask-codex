# Slice 09 — Live acceptance (revision 3)

Ticket: `.scratch/ask-codex-mvp/issues/09-live-acceptance.md` (spec Testing Decisions, Tier 2; notes moved from tickets 03 and 07; user decision on the execution mode). Envelope, F-map (F2, F8, F9, F10 and every "live" acceptance line), stops: `PLAN.md`. Blocked by 02, 03, 04, 06, 07, 08, 11 and 05 (**paused** by the user — its live scenario is recorded as observed). **Entry gate:** ticket 08's outcome verifier CONFIRMED and recorded. Risk triggers: real external calls through the user's Codex login; real MCP servers outside the sandbox → plan-verifier before, fresh verifier after.

Revision 2 fixes round 1 (REVISE, 5 blockers): named config files with backup, checks around every run, restore-and-stop, and a Rollback section; slice-local security stops with A2 first; a namespace list in A2; evidence printed before cleanup; an F8 baseline and a forced-stop probe with a narrowing fallback.

Revision 3 (dispositions of round 2 REVISE, both FIX): (1) the F8 post-stop snapshot is taken inside the stopping session while it is still running, and the I3 guide replaces `tasklist` with a baseline handoff plus an in-session snapshot; (2) A8b uses A2's exact command line, and stop 3 covers every default-policy scenario.

## Budget

- **Codex calls:** ≤ 16 in this ticket (program: 5 used of 25). Planned: automated 10 (A1 1, A2 1, A3 1, A4 2, A7 1, A8 1, A8b 1, A9 1, A10 1), interactive ≈ 3–4. A scenario whose call would exceed the budget is skipped and recorded.
- **Claude:** no dollar cap (user decision); one headless run per scenario.

## Safety

- **Guarded files.** `C:\Users\admin\.claude\ask-codex.json` (expected absent) and `D:\codex\config.toml` (the user's Codex config). Before the first scenario: record presence and SHA-256 of both and copy them to `D:\tmp\askcodex-live-09-backup\`. Files Codex rewrites by itself under `D:\codex` (model cache, sessions, logs) are not guarded.
- **Checks around every run.** Before and after each headless run, each direct `codex exec`, and each interactive session: compare presence and hash with the baseline. On any change: restore the backup, record it, and **stop before the next Codex call**.
- **Where.** Each scenario in its own project under `D:\tmp\askcodex-live-09\<scenario>` (R: cannot host Codex runs).
- **Headless runs.** `claude -p --plugin-dir <repo> --model claude-sonnet-5 --permission-mode acceptEdits --add-dir <scenario project> --add-dir <temp base> --allowedTools Bash Read Glob Grep Skill Write TaskOutput TaskStop --output-format stream-json --verbose`; each transcript saved outside the repo; excerpts go into ticket 09 Comments.
- **MCP.** No change to the user's MCP configuration; minimal-deny uses a project-level ask-codex config inside the throwaway project with the F12 confirmation in the prompt, and a question that needs no MCP tool (residual risk: other servers usable by instruction only — recorded).

## Stops (slice-local; each stops all further Codex calls, records the evidence, and pauses per global stops (4)/(7))

1. A2: `probe.txt` exists afterwards, or the `curl` call succeeds (F2 broken).
2. A2: the namespace list contains a disabled server or `mcp__codex_apps`.
3. Any default-policy scenario (A1, A2, A4, A7, A8, A8b, A9): an argv lacks `-s read-only`, `--ephemeral`, `--disable apps`, or a disable definition for a listed server, or the printed events show an MCP tool call.
4. A10: the argv disables anything other than `node_repl` and `cua_repl`.
5. A5, A6 or A11: any `codex` command runs.
6. A guarded file changed (restore first).
Order: **A2 runs first**; the skill scenarios follow only if A2 passes.

## Automated scenarios (Claude runs them headless)

For A1, A4, A7 and A10 the prompt adds: "Before you clean up, print every line of each events.jsonl that contains `mcp_tool_call` (or say there are none) and the full content of each last-message.json." After the run, a small script (`live-09-check.mjs`) validates each printed reply against the schema's required fields and types.

| # | Scenario | Calls | Pass evidence |
|---|---|---|---|
| A2 | Sandbox and namespaces probe (direct `codex exec` with A1's exact flags and disable set; not through the skill) — **first** | 1 | Codex is asked to (a) run `echo probe > probe.txt`, (b) run `curl -sS https://example.com`, (c) list its available tool namespaces/servers; afterwards `probe.txt` is absent, the events show the write denied and the network call failing, and the recorded namespace list contains none of blender, codex_app, comfyui, cua_repl, node_repl, pencil and no `mcp__codex_apps` |
| A1 | Manual consultation with a question (default policy) | 1 | argv has `-s read-only`, `--ephemeral`, `--json`, `--output-schema`, `-o`, `--disable apps`, a disable definition for every listed server, explicit effort; printed events: no `mcp_tool_call`; printed last-message passes `live-09-check.mjs`; reply has `MCP: all servers disabled…` and a disposition per claim; run dir removed |
| A3 | Manual consultation without a question (first headless turn sets the context without calling Codex; resumed second turn runs `/ask-codex:ask`) | 1 | the inferred question is shown in one line and matches the context |
| A4 | Parallel `astra, sol` | 2 | two runs, argv efforts `medium` / `high`, both with the full disable set; printed events and replies as in A1; merged reply with the fixed headings and full-slug tags |
| A5 | Ambiguous alias `5.6` | 0 | candidates from the real model cache; no `codex` command |
| A6 | Wrong model name (`model nova`) | 0 | error listing the available models; no `codex` command; nothing attributed to Codex |
| A7 | Follow-up (resume A1's session) | 1 | argv without `resume`/`fork`; stdin carried lines in the fixed form; status lines in the reply; printed evidence as in A1 (if A1 had no investigate claim, the prompt names another claim to re-check — recorded) |
| A8 | Timeout with `EVAL_ASK_CODEX_TIMEOUT_MINUTES=1` on a slow question | 1 | `Timeout override active:` line; either the confirmed-alive notice and a normal result, or the non-interactive stop with `Consultation stopped:` — if it stops, the F8 check below applies |
| A8b | Forced-stop probe for F8 (headless, not through the skill): start a slow direct `codex exec` in the background with **A2's exact command line** (`-s read-only`, `--ephemeral`, `--json`, `--disable apps`, one disable definition per server from the live `codex mcp list --json`; only the prompt differs), wait 20 s, `TaskStop` it — the mechanism the skill's stop path uses — then, in the same session, wait 5 s and take the post-stop snapshot (F8 check) before ending the turn | 1 | argv recorded and matches the list above; F8 check passes |
| A9 | Project path with spaces (F9): `D:\tmp\askcodex-live-09\space proj\` | 1 | the consultation completes; every path in the commands is quoted literally |
| A10 | MCP minimal-deny (project config + F12 confirmation) | 1 | argv disables only `node_repl` and `cua_repl`; minimal-deny statement in the reply; printed events: any MCP tool calls recorded |
| A11 | Project-layer Codex MCP definition with decline | 0 | not sent; the reply names the server from the project's `.codex/config.toml` |
| A12 | F10 | 0 | `codex --version` recorded (currently `codex-cli 0.154.0`) |

**F8 check.** Snapshot = PowerShell `Get-CimInstance Win32_Process -Filter "Name like 'codex%'"` → ProcessId, ParentProcessId, CreationDate, CommandLine. **Baseline:** the main session takes it right before launching A8/A8b, and before handing I3 to the user. **Post-stop snapshot:** taken **inside the stopping session while it is still running**. For A8b, and for A8 if it stops, the prompt tells the headless Claude to run the snapshot through Bash 5 s after `TaskStop` and before its final reply. For I3, the user runs it via `!` in the still-open interactive session (the command is in the guide). A snapshot taken after `claude -p` has exited does not count, because exit cleanup could mask a leak. Pass: the post-stop snapshot appears in that session's transcript after its `TaskStop` call and before its final `result` event (I3: before the user ends the session), and it lists no `codex` process that is absent from the baseline. If no scenario produces such a snapshot, F8 is recorded as "not verified live" and acceptance 5 excludes it.

Covered by earlier live evidence and not repeated: the allowed-lookup-server scenario (ticket 11's live run B) — referenced in the record.

## Interactive scenarios (the user performs them; guide `.scratch/ask-codex-mvp/plan/live-09-interactive-guide.md`)

- **I1 — Proactive consent** (ticket 05 paused; recorded as observed): Decline / Consent this once / Consent for this session across three fix-loop topics.
- **I2 — Override scope** (from ticket 03): the "this consultation only / rest of the session" question; a later consultation keeps the session choice.
- **I3 — Stall question** (from ticket 07): with the 1-minute override, choose "wait" once, then "stop"; F8 check: the user tells the main session before sending the slow consultation, the main session takes the baseline and replies "go", and after the stop the user runs the snapshot via `!` in the still-open interactive session (guide I3 steps 2 and 5).
Guarded-file checks run before Claude hands over and after the user reports done.

## Rollback

Restore the guarded files from `D:\tmp\askcodex-live-09-backup\` if changed; delete `D:\tmp\askcodex-live-09\` and the backup dir at the end; ticket-09 documentation and Comments are one commit (`git revert` undoes them). No other state is created (Codex runs are `--ephemeral`).

## Acceptance

1. Guarded-file checks pass around every run (or a restore-and-stop is recorded).
2. A1–A12 results recorded in ticket 09 Comments with evidence excerpts, the Codex version, and every deviation classified (skill defect → fix ticket or `/code-review` item; environment/limitation → README).
3. I1–I3 performed by the user and recorded (or recorded as not verified live).
4. Codex calls ≤ 16; probe projects and the backup deleted.
5. Fresh verifier CONFIRMED on the recorded results against ticket 09's criteria (F2 including namespaces, F8 per the F8 check or narrowed, F9, F10, and the moved items).
