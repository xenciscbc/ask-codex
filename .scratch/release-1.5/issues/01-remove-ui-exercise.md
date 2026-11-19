# 01 — Remove `/ask-codex:ui` and everything that exists only for it

Status: ready-for-agent
Spec: `.scratch/release-1.5/spec.md` — cites P3, D3, Plan review 1 dispositions (B2, B3, N1, N4, N5), Plan review 2 dispositions (N1, N7), I1, I2, I3, Out of scope, Overall acceptance
Blocked by: None
Security-critical: no (spec, Claim classification)

## What to do

Delete the UI exercise feature (D3), keeping the consultation path (`ask`, `review`, `discuss`) unchanged (I1).

**Delete whole:**
- `skills/ui/`
- `skills/ask/ui-exercise.schema.json`, `skills/ask/browser-server/`, `skills/ask/guard-page/`
- `skills/ask/scripts/`: `exercise.py`, `guard.py`, `install.py`, `repro.py`, `target.py`, `attach.py`, `browser.py`, `supervisor.py`, `winjob.py`, `mcp_stdio.py`, `redact.py`, `platform_layer.py`
- `evals/_harness/`: `exercise_app_test.py`, `exercise_attach_test.py`, `exercise_guard_test.py`, `exercise_platform_test.py`, `exercise_repro_test.py`, `exercise_run_test.py`, `exercise_target_test.py`, `ui-skill-graders.test.mjs`, `ui-attach-graders.test.mjs`, `stub/exercise_platform_fake.py`, `gen_ui_history.py`, `redact_oracle_460de71.py`
- every `evals/ui-*/` case directory (28 at the time of writing)

Before deleting a module, confirm by search that no kept file imports or references it. A module the consultation path uses is kept, and the finding is reported.

**Edit:**
- `skills/ask/scripts/consult.py`:
  - Remove the exercise imports, `cli()`, the `exercise.is_request` / `is_plan` branches in `prepare`, `run`, `wait_for`, `continue_wait`, `collect`, `stop` and `cleanup`, and `run_exercise`.
  - Remove `EXERCISE_ACTIONS`, `SECOND_ARGUMENT`, `result_bound` and the `--result` / `wait-result` machinery (`RESULT_BOUNDS`, `MAX_RESULT_WAIT`, `start_result`, `finish_result`, `wait_result`). Do this only after confirming that no kept skill passes `--result`.
  - Remove the exercise argparse actions and their branches in `main`, and the `file` positional argument.
  - The remaining actions are exactly `resolve`, `prepare`, `run`, `collect`, `wait`, `continue`, `stop` and `cleanup`. An extra positional argument is an argparse error.
  - Remove `mcp_get` and `which`. They are reached only through `cli()` from the exercise modules, and `consultation_test.py` asserts that a consultation never calls `mcp get`.
  - The no-replay `started` guard in `run`, the `execution-error.json` and failure-receipt logic in `main`, and `collect`'s consultation path keep their behaviour (I2, I3).
  - `EXEC_CONSTANTS`, the consultation `argv()` in `run`, `launch`, `snapshot`, `result_for` and `stop_codex` keep their behaviour.
  - The module docstring and comments no longer describe exercises.
- `skills/ask/SKILL.md`: remove the pointer line to `/ask-codex:ui`.
- `skills/setup/SKILL.md`: remove the exercise-preparation description clause, bullet, routing and procedure (the procedure uses `browser-install`, `exercise-deps` and `browser-start-check`). The MCP-policy half stays as it is.
- `.claude-plugin/plugin.json`: remove `./skills/ui`, the `/ask-codex:ui` sentence in `description` and the `ui-exercise` keyword. The version is not changed here (ticket 03).
- `README.md` and `README.zh-TW.md`: remove every ui and exercise passage. That covers the feature list, the Windows-only clause, the command list, the `skills/ui/` table row and copy-list items, prerequisites and usage, the whole "UI exercise" section, the UI validation paragraph, the `ui` mention in the localhost bullet, and the UI exercise known-risk bullet. The consultation validation table stays.
- `CONTEXT.md`: remove the exercise-only terms (演練, 可丟棄目標, 副本模式, 接上模式). Keep every term the consultation path uses.
- `docs/adr/0009-exercise-on-a-disposable-target.md`: set its status to superseded, because `/ask-codex:ui` was removed in 1.5.0. The body stays as history.
- `evals/_harness/setup-skill.test.mjs`: drop the assertions about exercise preparation, ADR 0009 content, the exercise CONTEXT terms, `./skills/ui` and the ui README sections.
  - The localhost assertions (around lines 81 and 91) check README text that this ticket changes. Rewrite them to match the new README sentence; do not drop them.
  - Keep every other assertion, and add one that `plugin.json` lists no `./skills/ui`.
- `evals/_harness/stub/codex-stub.py`: remove the exercise-only parts.
  - The browser-server definitions and the `cdt_*` keys (`browser_key`, `browser_definitions` and their checks).
  - The attach-mode lookup for `for_attach_targets`.
  - The exercise `records` handling.
  - `leave_process`.
  - The `mcp get` modelling: the stub's `def mcp_get`, its dispatch in `main`, and the `mcp_get_patch` and `mcp_get_prints_default_approval` keys. An `mcp get` call then becomes an unsupported-command violation, and `consultation_test.py`'s "never calls mcp get" assertion still holds. Its `mcp-get.log` check becomes vacuous; the empty-`violations.log` check carries the protection. Say so in a comment there.
  - `exercise_extra_enabled`.
  - The docstring passages describing these.

  Keep `guard_fails`: it is the consultation MCP guard (`consultation_test.py` uses it). Keep `exec.events` as generic scripted events emitted after `turn.started`, and reword its docstring without the attach tripwire. Any `-c` the stub no longer knows must still be reported as `unexpected -c`, so a stray exercise key on a consultation argv still fails.
- `evals/_harness/run-evals.sh`: remove the exercise copy and generation lines and their comment.
- `evals/_harness/consultation_test.py`: keep the regression test that consultation argv carries no `cdt_`, `approval_mode` or `ui-exercise` keys. Its comment may be simplified. `BASELINE_ARGV` is unchanged in this ticket.

## Acceptance

1. None of the deleted paths exists.
2. A search of `skills/`, `.claude-plugin/`, `README.md`, `README.zh-TW.md`, `CONTEXT.md` and `evals/_harness/` finds none of these: `ask-codex:ui`, `ui-exercise`, `exercise.py`, `browser-install`, `exercise-deps`, `browser-start-check`, `--result`, `wait-result`, `import exercise`, `def mcp_get`, `def which`, `leave_process`, `for_attach_targets`, `mcp_get_patch`, `exercise_extra_enabled`.

   Only two hits are allowed:
   - the regression keys that `consultation_test.py` keeps (`cdt_`, `approval_mode`, `ui-exercise`) in its test that consultation argv carries none of them;
   - the generic rule that Codex never controls a browser.
3. `python skills/ask/scripts/consult.py --help` lists exactly the eight actions above, with no `--result` option and no `file` argument.
4. I1: `BASELINE_ARGV` in `evals/_harness/consultation_test.py` is byte-identical to the base revision, and its tests pass.
5. I2 and I3 still hold, shown by the existing tests passing unchanged:
   - `test_parallel_mixed_result_keeps_success_and_no_retry` (a second `run` fails);
   - the collect and classify tests in `consultation_test.py`.
6. The full offline suite passes, as the spec's Overall acceptance names it. It is named here because this ticket changes shared test support (`stub/codex-stub.py`, `run-evals.sh`).
7. D3 docs:
   - `docs/adr/0009-exercise-on-a-disposable-target.md`'s status line says it is superseded by the removal of `/ask-codex:ui` in 1.5.0.
   - `CONTEXT.md` contains none of the terms 演練, 可丟棄目標, 副本模式, 接上模式.

## Comments
