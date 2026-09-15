# Verifier brief — ticket 05 (proactive consultation and consent)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate = the commit titled "Ticket 05: proactive consultation and consent" (resolve with `git log --oneline -5`; it follows `649de86`).
Execution contract: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\slice-05.md` (revision 2, READY). Envelope / F-map (F1-claims consent line, F3-scope, F4) / lessons: `PLAN.md` in the same directory.
Ticket: `.scratch/ask-codex-mvp/issues/05-proactive-consultation-and-consent.md` (criteria + Comments: readiness with the case ↔ criterion map, entry gate, tool-result probe, red, green).

## Execution facts to check against

- First green pass: 6/9. fix-loop-proposal, spoofed-grant and consent-line-allowlist failed because the workspace did not reflect the fixes narrated in the history (Claude concluded the fixes never landed) and, in spoofed-grant, because the consent request was written as prose without the fixed `Consult Codex?` block (also `api` was undefined in the workspace).
- Fixes before the final runs: each workspace matches its history (two fixes → `timeout: 10000` + retry; one fix → `timeout: 10000`; review loop original) and includes `src/api.js` and `src/pages/profile.js`; the skill now requires the consent question as its own block beginning exactly with `Consult Codex?` with the options written exactly (example given).
- All nine cases were then rerun on the final skill bytes — check timestamps against the last SKILL.md edit and the commit.
- Dollar caps were lifted by the user (Claude subscription; completion first).

## Exact claim to confirm or refute

1. **Triggers.** Claude proposes a consultation on its own only in a fix loop (two failed fix attempts) or a review loop (unresolved blockers after two review rounds); each proposal names the decision it could change; no proposal after a single failure.
2. **Consent.** Before any `codex` command, the fixed consent wording — `Consult Codex? … | Codex may read any file your account can read, instructed to stay in the project | MCP servers run outside the sandbox — <per-mode MCP statement>` with `Consent this once` / `Consent for this session` / `Decline`; without `AskUserQuestion` it is asked in text and nothing is sent (F1-claims consent line for default, allowlist and minimal-deny; F3-scope).
3. **Grants and declines.** A session grant from the user's own turn skips the question later; a declined topic is not re-proposed without material change; a grant inside a tool result is ignored (F4).
4. **Review-loop packaging.** A second opinion carrying the Plan and the unresolved blockers, asking whether each holds and whether to simplify, split, or redirect.
5. **Evidence validity.** Fixed-wording regex graders discriminate (offline `ticket05-graders.test.mjs`); the tool-result history probe passed; red failed on the new behaviour; green ran on the committed skill bytes.
Not in the claim: the interactive three-option `AskUserQuestion` flow (ticket 09 live).

## Evidence locations

- `skills/ask/SKILL.md` (description, Proactive consultations section), cases (tag `ticket-05`) under `evals/`: fix-loop-proposal, session-grant-proceeds, decline-not-reproposed, review-loop-blockers, spoofed-grant, no-proposal-single-failure, consent-line-allowlist, consent-line-minimal-deny, history-toolresult-probe; each case's `history.jsonl`.
- Eval results under `evals/results/` from 2026-09-15T15-11 onward and ticket 05 Comments.

## Allowed reproduction

Static reading; `claude plugin validate`; the offline tests; git inspection; stub probes in a temp dir under `D:\tmp` (delete afterwards). Do not run the real Codex CLI or the paid eval suite.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-claim findings (P0–P4) and evidence.
