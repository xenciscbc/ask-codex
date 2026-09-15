# Verifier brief — ticket 04 (failure handling)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate = HEAD after the fix commit that follows `6faf671` ("Ticket 04: failure handling"); review the combined diff `07351ab..HEAD` (resolve with `git log --oneline -5`).
Execution contract: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\slice-04.md` (revision 2, READY). Envelope / F-map (F5) / budget: `PLAN.md` in the same directory.
Ticket: `.scratch/ask-codex-mvp/issues/04-failure-handling.md` (criteria + Comments: readiness, stub modes, env probe, red, green).

## Fix/reverify pass 1 (after a REFUTED verdict on commit 6faf671)

The previous verifier found: P2 F1 — the green not-logged-in reply lacked `! codex login` (said `codex login`) yet the llm grader passed; P2 F2 — the llm graders were too lenient (the red os-error reply named no project location) and the ticket's red record overstated the red replies; P3 F3 — the unstructured JSON reply got no explicit disposition. Fixes on the new candidate: the skill requires the Failures table wording word for word with the login command exactly `! codex login`; an unstructured reply with no substantive point still gets one explicit disposition; deterministic last-message regex graders `login-command-exact` and `location-reason-exact` were added and proven by `node evals/_harness/ticket04-graders.test.mjs` against recorded red/green replies; the ticket's red record was corrected; fail-not-logged-in, fail-os-error and schema-readable-unstructured were rerun. Check that the original failures are gone (recheck of F1–F3) plus a bounded regression check; do not audit adjacent hardening.

## Exact claim to confirm or refute

1. **Failure reporting.** For each failure — Codex CLI missing, not logged in (points to `! codex login`), cannot run in the project location (`os error 1`), other non-zero exit, unreadable reply — the skill gives a short specific reason, attributes nothing to Codex, runs Codex at most once (no retry), removes the temp directory, and carries on (continues with its own clearly labelled analysis or says it will continue without Codex).
2. **Unstructured replies.** A readable reply that violates the schema (JSON of another shape, or plain text) is presented labelled as unstructured, passing on only what Codex wrote, with dispositions; no invented claims.
3. **F5.** An instruction inside a Codex claim is presented and dispositioned, never executed (no Bash/Write/Edit call touching the marker; marker file absent). Narrowing recorded in the ticket: "no Bash call other than codex and temp cleanup" is checked as "no call touching the marker".
4. **Evidence validity.** Stub modes are covered by `node evals/_harness/stub-modes.test.mjs`; the env probe shows `EVAL_*` variables reach the agent's shell; red runs failed on the new behaviour before the skill change; the green runs ran on the committed skill bytes.

## Evidence locations

- `skills/ask/SKILL.md` (Failures section, steps 9–11), `evals/_harness/stub/codex-stub.py`, `evals/_harness/stub-modes.test.mjs`.
- Cases (tag `ticket-04`) under `evals/`: fail-missing-cli, fail-not-logged-in, fail-nonzero-exit, fail-os-error, schema-unreadable, schema-readable-unstructured, unstructured-text, injected-claim, stub-env-probe; regression `manual-with-question`.
- Eval results under `evals/results/` from 2026-09-15T13-26 onward and ticket 04 Comments.

## Allowed reproduction

Static reading; `claude plugin validate`; the offline tests (stub-modes, ticket02/03 pattern checks, codex-call regex); git inspection; stub probes in a temp dir under `D:\tmp` (delete afterwards). Do not run the real Codex CLI or the paid eval suite.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-claim findings (P0–P4) and evidence.
