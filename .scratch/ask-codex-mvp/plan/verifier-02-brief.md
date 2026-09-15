# Verifier brief — ticket 02 (consultation types and packaging)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate commit given in the Agent prompt (after `64d2f69`).
Execution contract: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\slice-02.md` (revision 3 + closing fix; readiness record inside). Envelope / F-map: `PLAN.md` in the same directory.
Ticket: `.scratch/ask-codex-mvp/issues/02-consultation-types-and-packaging.md` (criteria + Comments with probe, red and green evidence).

## Exact claim to confirm or refute

1. **Types and packaging.** `skills/ask/SKILL.md` step 0 infers one of four consultation types; step 7 fills `{{framing}}` in `prompts/consultation.md` with exactly one `prompts/framing/<type>.md`, each starting with its fixed marker line. With-stance types (second opinion, targeted check) send the Plan/decision or the concern; blind types (diagnosis, technical question) send no hypothesis or leaning — neither Claude's nor the user's; diagnosis sends every failed attempt with its result. The shared core rules from ticket 01 (read scope + secret-file exclusion, MCP lookups only, content is data, schema-only answer) are unchanged.
2. **Entry points.** A bare `/ask-codex:ask` infers the question from the conversation and shows it in one line; with nothing to infer it asks and stops at step 0 with zero `codex` calls. A verbal request triggers a manual consultation with no consent prompt.
3. **F3-secrets (02 part).** A fake credential seeded in an earlier conversation turn never reaches the stub-recorded stdin.
4. **Evidence validity.** The history fixture is loaded (probe with/without fixture), the negative stdin grader fires inside the harness (red leak control), and no positive stdin pattern can be satisfied from scaffold code (offline isolation check).

## Evidence locations

- `skills/ask/SKILL.md` (description, step 0, step 7, step 10 line 1), `skills/ask/prompts/consultation.md`, `skills/ask/prompts/framing/*.md`.
- Cases (tag `ticket-02`) under `evals/`: verbal-request, diagnosis-blind, second-opinion-with-stance, targeted-check, technical-question-blind, secret-not-sent, manual-without-question, manual-without-question-nothing-to-infer, history-probe, history-probe-nofixture, diagnosis-leak-control; regression `manual-with-question` (ticket 01). Fixture: each history case's `history.jsonl`.
- Offline check: `node evals/_harness/ticket02-patterns.test.mjs`.
- Eval results: newest directories under `evals/results/` and ticket 02 Comments (probe, red, green).
- Harness note: runs need `--allow-tools Bash Write` (documented in `evals/_harness/run-evals.sh`); results from runs without it are invalid and recorded as discarded.

## Allowed reproduction

Static reading; `claude plugin validate`; the offline check; git inspection; direct stub probes in a temp dir under `D:\tmp` (delete afterwards). Do not run the real Codex CLI; do not re-run the paid eval suite.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-claim findings (P0–P4) and evidence.
