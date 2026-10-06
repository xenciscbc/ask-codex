# 10 — Interactive discussion paths are verified against the skill text only

Status: resolved — A and B passed interactively; C not run by decision (2026-10-06); see Comments

**What to build:** the harness runs headless, so these discussion paths were never exercised end to end: the `AskUserQuestion` round-limit question (3 / 5 / 7 / custom, custom out of range re-asked), an out-of-range `rounds <n>` re-asked interactively, a mid-discussion `confirmation_required` asked and the same round continued, a liveness `decision_required` where the user chooses to stop (and the partial report that follows), and an unconfirmed stop. Run them once in an interactive session (the user typing the command), following the live-testing guards (config.toml hash and bytes, Codex PID baseline, throwaway repo under `D:\tmp`).

**Blocked by:** None — can start immediately.

- [ ] One interactive discussion without `rounds <n>`: the question appears with 3 / 5 / 7, a custom 1 is refused and re-asked, the chosen limit is reported.
- [ ] One interactive stop at a liveness decision ends the discussion with the partial report (`Round <n>: did not complete — …`, open points `(unresolved because the discussion ended)`), and the process tree is confirmed ended.
- [ ] Mid-discussion confirmation, if a project-defined server can be staged safely; otherwise record why not.

## Comments

- 2026-10-06 — Run by the user in interactive Claude Code sessions on the released 1.3.0 plugin (cache `ask-codex/1.3.0`, discuss SKILL.md sha `4bf9a8d6…`), throwaway repo `D:\tmp\discuss-interactive` (`interactive-setup.sh`, `interactive-check.sh`). Evidence: `evidence/interactive-A-trace.jsonl`, `interactive-B-trace.jsonl`, `interactive-guards.txt`.
  - **A — round-limit question:** `/ask-codex:discuss <topic>` without `rounds` → one `AskUserQuestion` with exactly 3 / 5 / 7; custom `1` → "a discussion needs 2 to 10 rounds" and the same question again; custom `2` accepted; report `Round limit: 2` noting the refused 1; 2 Codex calls; three headings; a both-marked user call reported `(your preference or authority)`.
  - **B — stop at a liveness decision:** with `EVAL_ASK_CODEX_TIMEOUT_MINUTES=1`, `wait` returned `decision_required` after 60 s; Claude asked Stop (Recommended) / Wait; the user chose Stop; the background stop returned `confirmed_stop`, `confirmed: true`, evidence `captured_identities_absent` (elapsed 86 s, last event `command_execution` 16 s before); the partial report has `Round 1: did not complete — …` with the stop details, `## Agreed` none, and L1–L9 under `## For you to decide` each `(unresolved because the discussion ended)` with `Codex recommends: none returned`; Claude's one-sided user call (L8) was correctly not treated as both-marked. Note: Claude read "Before answering, run Start-Sleep -Seconds 240 once" as an instruction to itself (ran it in the background and left it out of the topic); the 1-minute interval still produced the decision, so the path was exercised as intended.
  - **Guards:** no leftover `codex exec` process after either test; user ask-codex.json absent before and after; the throwaway repo unchanged; `config.toml` differed only in `SKY_CUA_NATIVE_PIPE_DIRECTORY`, rewritten when the Codex app restarted at 09:31 (its three new service processes share parent PID 37764).
  - **C — mid-discussion confirmation:** not run, by decision: staging it needs a project-defined MCP server whose definition changes during a running discussion, i.e. editing real MCP configuration on this machine. The rule remains checked against the skill text only.
