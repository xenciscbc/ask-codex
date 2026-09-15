# Verifier brief — ticket 01, F6 closure (fresh pass)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`. Candidate commit: given in the Agent prompt (it follows 0fb4a89).

## Original finding (previous verifier, REFUTED on F6 only, P2)

Per-case stub-record graders were incomplete: `mcp-guard-blocks` had no "exec.sentinel absent" grader; `project-layer-aborts-01` checked only `mcp-list.log` absent; `project-defined-server` had no "mcp-list.log present" grader; and the CODEX_CALL regex missed path-prefixed (`./stubbin/codex exec`, `/…/.eval-stub/codex mcp`) and quoted (`"codex" exec`, `'codex' exec`) invocations, so the sentinel was the only backstop and it was missing. Advisories A1 (no offline check for a missing `--disable apps`), A2 (stub accepted effort `low` and a repeated `-s`), A4 (doc-check wording), A5 (no cleanup grader on abort paths) were also raised; A3 (rule-(c) wording) was deferred to ticket 11.

## Changes to check

- `evals/mcp-guard-blocks/graders/no-exec-sentinel.md`, `evals/project-layer-aborts-01/graders/no-exec-sentinel.md` (`file_exists … exists: false`), `evals/project-defined-server/graders/list-log-present.md`.
- CODEX_CALL regex broadened in every grader that uses it and in `evals/_harness/codex-call-regex.test.mjs` (now 7 negative / 10 positive samples, including path-prefixed and quoted forms).
- Stub (`evals/_harness/stub/codex-stub.py`): violation when `--disable apps` is missing, when effort is below `medium`, and when `-s`/`-C`/`-o`/`--output-schema`/`-m`/`--disable` is repeated.
- Cleanup graders on both abort cases (`temp-cleanup.md`).
- Ticket 01 Comments: doc-check note (A4) and the rerun results; ticket 11 Comments: A3 deferral.
- `skills/ask/*` unchanged since 0fb4a89.

## Exact claim

F6 now holds: every ticket-01 eval case asserts exactly the stub records it should have and none it should not (manual-with-question and project-defined-server: list log + exec sentinel present, no violations; mcp-guard-blocks: list log present, exec sentinel absent, zero `codex exec`; project-layer-aborts-01: zero `codex` calls, no list log, no exec sentinel), the CODEX_CALL regex catches path-prefixed and quoted invocations, and the stub flags the A1/A2 cases. The final eval run on the candidate commit passes all four cases (results under `evals/results/`, newest directory). The other ticket-01 rows remain as previously CONFIRMED (skill bytes unchanged).

## Allowed reproduction

`node evals/_harness/codex-call-regex.test.mjs`; direct stub probes with crafted argv in a temp dir under `D:\tmp`; reading `evals/results/<newest>/aggregate-result.json`. Do not run the real Codex CLI; do not re-run the paid eval suite.
