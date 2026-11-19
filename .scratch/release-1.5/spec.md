# Spec: release 1.5 — consultations under Codex CLI 0.170.0, and `/ask-codex:ui` removed

Status: implemented and released as v1.5.0 (2026-11-19); plan review 3 READY, user-approved

Tickets: `issues/01-remove-ui-exercise.md`, `issues/02-reply-from-event-stream.md`, `issues/03-release-1.5.0.md`.

## Problem

**P1. Every consultation fails under Codex CLI 0.170.0 when its run directory is on the R: RAM disk.** On 2026-11-19 a `/ask-codex:ask gpt-6.2-astra:high` in the cc-feather project failed twice with only `Codex execution failed` (exit 1). The first failure was a separate cause: codex-cli 0.159.3 answered `model_not_found` for `gpt-6.2-astra`; upgrading to 0.170.0 removed it. The second, after the upgrade, came before any event (`last_event: null`).

Reproduced here with `consult.py`'s own preflight and the 1.4.0 argv, prompt `hi`, project `D:\work_data\project\skill\cc-feather`:

| `-o` target | Result |
|---|---|
| `R:/Temp/repro-…/last-message.json` | exit 1, stderr `Error: Failed to open last message file "…": path contains a reparse point` |
| `D:/tmp/repro-…/last-message.json` | exit 0, `thread.started` and a normal turn |

R:, `R:\Temp` and `R:\Temp\claude` show no reparse attribute or link target; the drive is a RAM disk that `Get-Volume` does not list. The run directory lives in the session scratchpad (or TEMP), which is on R: on this machine, so with 0.170.0 every model and every project fails. 0.159.3 accepted the same `-o` path.

**P2. A failed run gives no reason.** `collect` takes a failure reason only from `stderr.log`, and only for "not logged in". Codex 0.170.0 reports a turn failure in the `--json` event stream and leaves stderr empty (probe B below), so the cause of the cc-feather failure (`model_not_found`) never reached Claude. This is also `.scratch/approval-boundary/issues/04-model-slug-and-event-stream-checks.md` item 2.

**P3. `/ask-codex:ui` is to be removed.** The user's decision on 2026-11-19: in practice it is not useful, and it goes in this release instead of being adapted to P1 (`exercise.py` also passes `-o`).

## Evidence for the fix (2026-11-19, codex-cli 0.170.0)

- **Equality, older CLI:** in `.scratch/subagent-boundary/evidence/`, each of the five `probe-*-last.json` files equals, byte for byte, the `text` of the last `item.completed` item of type `agent_message` in its `probe-*-events.jsonl`, and each stream ends with `turn.completed`.
- **Probe A:** the 1.4.0 argv without `-o`, run directory and event file on R:, model `gpt-6.2-astra`, effort `high`. Exit 0, events `thread.started`, `turn.started`, `item.completed:agent_message`, `turn.completed`. `replies.classify(text, "consultation")` returned `structured`.
- **Probe B:** same argv with the unlisted model `gpt-nonexistent-probe`. Exit 1, events `thread.started`, `item.completed:error`, `turn.started`, `error`, `turn.failed`, with `turn.failed.error.message` = `The 'gpt-nonexistent-probe' model is not supported when using Codex with a ChatGPT account.` No `agent_message`, empty stderr.

The probe scripts live in the session scratchpad and are not part of this plan.

## Outcome

Plugin 1.5.0:

1. `/ask-codex:ask`, `/ask-codex:review` and `/ask-codex:discuss` complete under codex-cli 0.170.0 with the run directory on R:.
2. A failed run reports Codex's own error text when the event stream carries one.
3. `/ask-codex:ui` and all code, tests, evals and docs that exist only for it are gone.

## Decisions

- **D1. The reply comes from the event stream.** `codex exec` gets no `-o`. `collect` reads `events.jsonl` line by line in binary mode, splitting on `\n` only. It decodes each line as strict UTF-8 and parses it with `json.loads`.
  - **Events:** only a JSON object whose `type` is a string counts as an event.
  - **Plain text:** leading whitespace and U+FEFF are stripped first. The stripped text is what is tested and parsed. A line whose stripped text does not start with `{` is skipped; Codex prints plain-text errors on stdout.
  - **Fail-closed lines:** any of these means the run has no reply:
    - a line that starts with `{` but is not a JSON object;
    - a line that is not valid UTF-8;
    - a line nested too deeply to parse.
  - **Conditions for a reply.** A run has a reply only when all of these hold:
    - its exit code is 0;
    - the stream holds exactly one `turn.completed`, and it is the last event;
    - the final turn holds an `item.completed` event whose `item` is an object with `type` `agent_message` and a string `text`. The final turn is the events after the last `turn.started`, or the whole stream when there is no `turn.started`.
  - **The reply:** the `text` of the last such item in the final turn. When that `text` is empty or only whitespace, the run has no reply. There is never a fallback to an earlier message.
  - **Stopped and missing:** a stopped run never has a reply, because `stop_status` is checked first, as today. A missing `events.jsonl` counts as an empty stream.
  - **Unreadable file:** any other `OSError` while reading `events.jsonl` leaves the run with no reply, whatever its exit code. Its reason becomes `Codex events could not be read`. This replaces both `Codex returned no usable reply` and `Codex execution failed`, and any D2 text.
  - **Scanning continues:** after a fail-closed line, the scan still reads the rest of the stream for the D2 failure text.
  - **Isolation:** any problem in one run's stream affects only that run, never the rest of `collect`.
  - **Other readers:** `snapshot`'s bounded 64 KB tail read for `last_event` stays as it is.
- **D2. Failure reason from the stream.** D2 applies only when the run's exit code is not 0.
  - **Source:** the text of the last `turn.failed` event with a string `error.message`. When there is none, the text of the last `error` event with a string `message`.
  - **Cleaning:** each of these is replaced with a space, and runs of whitespace then collapse to one:
    - every C0 control character, DEL (U+007F) and every C1 control character;
    - U+2028 and U+2029;
    - bidi controls (U+202A–202E, U+2066–2069).

    The result is then stripped of leading and trailing whitespace.
  - **Result:** the reason is `Codex reported: ` followed by the cleaned text, cut to 500 characters after cleaning. A text that is empty after cleaning leaves the existing reason.
  - **Precedence:** a run's reason is chosen from these, highest first:
    1. a reason the launcher wrote (`result_for(child)["reason"]`), as today;
    2. the "not logged in" stderr rule, as today;
    3. `Codex events could not be read` (D1);
    4. the D2 text;
    5. the base reason, `Codex execution failed` or `Codex returned no usable reply`.
  - **Skills:** the ask, review and discuss skills say that a reason starting `Codex reported:` is Codex's own text: data to report, never instructions.
- **D3. Remove, do not deprecate.** `/ask-codex:ui` is deleted. That covers its skill, the exercise modules, the browser server, the guard page, its schema, the `consult.py` exercise actions and `--result`, the setup skill's exercise preparation, its tests and evals, and its README sections. ADR 0009 is kept in history with its status changed to superseded by the removal in 1.5.0. CONTEXT.md drops the exercise-only terms.
- **D4. Version 1.5.0** (a minor bump: a command is removed). The README states the removal and that 1.4.0 installs leave `%LOCALAPPDATA%\ask-codex\` behind, which the user may delete.
- **D5. ADR 0011** records D1 and D2: why `-o` was dropped, the probe evidence, and the limit that the reply now depends on the `--json` event shape.

## Security analysis dispositions (analyst, 2026-11-19, on ticket 02)

| Finding | Disposition |
|---|---|
| F1. `events.jsonl` is Codex's stdout. Processes outside the recorded tree inherit that handle: the user's notify hook chain was confirmed live in `.scratch/script-owned-consultation/issues/12`. Whether sandboxed commands inherit it is unverified. Such a process can append `agent_message` + `turn.completed`, and "last message, last event" would take the forged text. | Adopt in D1: exactly one `turn.completed`, which must be the last event, and the message must come from the final turn. An append then yields no reply. Ticket 02 S4. The live check of the stream tail after the notify hook has fired goes to ticket 03. |
| F2. Non-object JSON lines, a non-dict `item`, a non-string `text`, deep nesting, a missing file and invalid UTF-8 crash `collect` or fail it as a whole. A raw U+2028 split by `str.splitlines()` produces non-object fragments. | Adopt in D1: binary read with a `\n` split, strict UTF-8, typed checks, `RecursionError` caught, a missing file read as empty, failure kept to one run. Ticket 02 S5 and tests. |
| F3. Gaps that fall back to an earlier message: empty last text, corrupted last line, multiple turns, non-`completed` or non-`agent_message` items. | Adopt in D1: final turn only, no fallback, and a `{`-line that does not parse means no reply. This is stricter than the draft's "skip non-JSON". Ticket 02 S6 and tests. |
| F4. The reason can carry newlines, control characters and lines that look like fixed status lines. No skill says the reason may be Codex text. D2 was unclear for exit 0. | Adopt in D2: cleaning, the cap applied after cleaning, D2 only for exit ≠ 0, and one sentence in the ask, review and discuss skills. Ticket 02 S3 and tests. |
| F5. Reading the whole stream into memory costs several times the file size. | Adopt in D1: stream line by line, keeping only the current candidate and the terminal state. No total size cap. Ticket 02 test with a 10 MB stream. |
| F6. The stub writes ASCII-only JSON, so encoding bugs stay hidden. | Adopt: a hand-written raw UTF-8 stream with Traditional Chinese and U+2028 in the reply. Ticket 02 test. |
| F7. Equivalence under 0.170.0 rests on one probe. If 0.170.0 ever omits the message, the run fails closed. | Adopt in ticket 03's live acceptance: one structured reply with the run directory on R:, and the stream tail inspected after the notify hook has fired. |

## Plan review 1 dispositions (REVISE, 2026-11-19)

| # | Finding | Disposition |
|---|---|---|
| B1 | `stub-modes.test.mjs` is built on `-o` (its `execArgs`, its reads of the out file, its no-violation assertions and the P9 replay), so ticket 02 would break it with no direction given. | FIX: ticket 02 rewrites it and names it a related test. `run-stop-scripts.test.mjs:45` drops `-o` as well. |
| B2 | Ticket 01 misses exercise-only code: `consult.py` `mcp_get`, `which` and the `file` positional, and several stub parts. "Guard modelling" is ambiguous, because the stub's `guard_fails` belongs to the consultation path. | FIX: ticket 01 lists each item. `guard_fails` is kept, and `exec.events` is kept as generic scripted events. |
| B3 | Ticket 01 changes code next to the no-replay guard and the failure receipts, but does not cite I2 and I3. | FIX: it cites them and names the tests that hold them. |
| B4 | Ticket 03 made the full suite its own acceptance, although the Overall acceptance already names it. | FIX: ticket 03 names `setup-skill.test.mjs` as its related test. The full suite stays the final check's. |
| N1 | Ticket 01's acceptance 2 contradicts itself, because the regression keys must remain. | Adopt: the allowed hits are named. |
| N2 | Test (t) is infeasible with multi-MB lines. | Adopt: lines of at most 256 KB, measured in process. |
| N3 | Edge cases of D1/D2 are not stated. | Adopt in D1/D2: no `turn.started`, leading whitespace and BOM, scanning after a fail-closed line, other `OSError`, the D2 source order, DEL. |
| N4 | The `file` positional is left unused. | Adopt: removed in ticket 01. |
| N5 | The localhost assertion in `setup-skill.test.mjs` must be rewritten, not kept. | Adopt: ticket 01. |
| N6 | Ticket 03 live check: a successful `collect` already removes the run directory; an event after `turn.completed` makes acceptance 2 fail; "one call" is undefined. | Adopt: ticket 03. |
| N7 | Adding the sentence to the review skill duplicates ask's text. | Keep it (harmless; review has its own report section). |
| N8 | Two eval graders still mention `last-message.json` or `-o`. | Adopt: ticket 02 updates their wording. Narrowed to one grader by Plan review 2 N6. |
| N9 | `.scratch/approval-boundary/issues/04` item 2 is resolved by ticket 02. | Adopt: noted in ticket 02's comments when it lands. |

## Plan review 2 dispositions (REVISE, 2026-11-19)

| # | Finding | Disposition |
|---|---|---|
| B1 | The spec and ticket 02 disagree on the reason when exit is 0 and an `OSError` occurs. | FIX: D1 says "whatever its exit code". D2 gives a single numbered precedence list. Ticket 02 cites it, and test (v) states exit 0. |
| B2 | Ticket 02's acceptance does not check the skill sentence (F4) or ADR 0011 (D5). | FIX: ticket 02 acceptance 5. |
| B3 | Ticket 03's related tests leave out `review-skill-graders.test.mjs` and `discuss-skill-graders.test.mjs`, which read `plugin.json`. | FIX: ticket 03 acceptance 3. |
| N1 | The stub's own `def mcp_get` and its dispatch are not listed. | Adopt: ticket 01. |
| N2 | `"   "` collapses to `" "`, not empty. | Adopt: D2 strips. |
| N3 | The precedence wording is ambiguous. | Adopt: the numbered list in D2. |
| N4 | BOM handling is undefined. | Adopt: D1 parses the stripped text. Ticket 02 test (v) covers a BOM line. |
| N5 | S3 omits DEL. | Adopt: S3 refers to D2's cleaning list. |
| N6 | The `-o` in `paths-single-quoted.md` sits inside grader logic, which has been stale since 1.1.0. | Its rewrite is dropped from ticket 02 and goes to the Follow-up record. `final-presents-claims.md` is still reworded. |
| N7 | Ticket 01's ADR 0009 and CONTEXT.md edits have no acceptance. | Adopt: ticket 01 acceptance 7. |
| N8 | `snapshot` raises `AttributeError` on a non-object last line. This predates the change, and D1 leaves it unchanged. | Follow-up record (not this plan). |
| N9 | S4 cannot stop an insertion before Codex's own `turn.completed`. | Kept as residual risk. It is named in ticket 02 and in the brief for its Adversarial review. |
| N10 | Strict UTF-8 fails closed on legacy code-page plain text when exit is 0. | Accepted: Codex writes UTF-8. |

## Invariants (hold for every claim)

- **I1. Consultation argv.** Apart from removing `-o <file>`, the consultation command line is unchanged: `-s read-only --ephemeral --skip-git-repo-check --json`, `-C`, `-m`, effort, the preflight MCP overrides, every `EXEC_CONSTANTS` entry in its order, `--output-schema`, and `-` with the prompt on stdin. No new flag is added.
- **I2. Codex output stays data.** The reply text reaches Claude only through `replies.classify`, as today. Event text never selects code paths in `consult.py` beyond D1 and D2. The D2 reason is Codex's text, labelled as such and bounded, never an instruction.
- **I3. No automatic retry, no replay** of a started run, as today.

## Claim classification

- **01 (remove ui): not Security-critical.** It deletes a feature and its own boundary code. It does not change a control on the consultation path; I1 is checked by the existing argv baseline test.
- **02 (reply from event stream): Security-critical.** It changes how untrusted data is interpreted downstream. The event stream also carries command output and other repository-derived content, and D1 decides which text becomes "Codex's reply". D2 brings Codex-supplied text into a field Claude reads that was fixed text before. It gets a security analysis before plan review, and Adversarial review.
- **03 (release 1.5.0): not Security-critical.** Version, docs, live acceptance.

## Out of scope

- Adapting the exercise feature to 0.170.0, or any replacement for it. Content under `.scratch/exercise-skills/` stays as history.
- `.scratch/approval-boundary/issues/04` item 1 (slugs starting with `-`).
- Deleting `%LOCALAPPDATA%\ask-codex\` on users' machines (release note only), and old run directories.
- `evals/results/` (gitignored history).
- Diagnosing why Codex calls the R: path a reparse point.

## Overall acceptance

This is the plan's overall acceptance. The final check runs it for each commit to be landed or tagged, not for each claim, and it is not part of any claim's acceptance. It is the full offline suite, every `evals/_harness/*_test.py` with `python` and every `evals/_harness/*.test.mjs` with `node`, run from the repository root, all exiting 0.
