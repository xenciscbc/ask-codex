# 10 — Interactive discussion paths are verified against the skill text only

Status: needs-triage

**What to build:** the harness runs headless, so these discussion paths were never exercised end to end: the `AskUserQuestion` round-limit question (3 / 5 / 7 / custom, custom out of range re-asked), an out-of-range `rounds <n>` re-asked interactively, a mid-discussion `confirmation_required` asked and the same round continued, a liveness `decision_required` where the user chooses to stop (and the partial report that follows), and an unconfirmed stop. Run them once in an interactive session (the user typing the command), following the live-testing guards (config.toml hash and bytes, Codex PID baseline, throwaway repo under `D:\tmp`).

**Blocked by:** None — can start immediately.

- [ ] One interactive discussion without `rounds <n>`: the question appears with 3 / 5 / 7, a custom 1 is refused and re-asked, the chosen limit is reported.
- [ ] One interactive stop at a liveness decision ends the discussion with the partial report (`Round <n>: did not complete — …`, open points `(unresolved because the discussion ended)`), and the process tree is confirmed ended.
- [ ] Mid-discussion confirmation, if a project-defined server can be staged safely; otherwise record why not.
