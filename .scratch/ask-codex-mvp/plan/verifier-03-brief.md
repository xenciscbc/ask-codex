# Verifier brief — ticket 03 (model aliases and effort rules)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate = the commit titled "Ticket 03: model aliases and effort rules" (resolve with `git log --oneline -5`).
Execution contract: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\slice-03.md` (revision 2, READY). Envelope / F-map (F9) / budget: `PLAN.md` in the same directory.
Ticket: `.scratch/ask-codex-mvp/issues/03-model-aliases-and-effort-rules.md` (criteria + Comments: readiness, probe/route A, red, green).

## Exact claim to confirm or refute

1. **Model resolution in step 0, before any `codex` command.** The model-token rule (only the request's start names a model; `model <x>`/`use <x>`, a `:` word, or a word whose head is a listed slug or a contiguous run of its parts; everything else is question text) is in `skills/ask/SKILL.md`; aliases resolve against listed (`visibility: "list"`) models of `<Codex home>/models_cache.json` only — no hardcoded alias table; ambiguous → candidates asked, no codex call; no match → error listing the listed models, no codex call; no model named → session setting, else `config.toml` `model`, else lowest-priority-number listed model.
2. **Effort rules.** Always explicit; the Codex config's effort never reaches argv; floor `medium`; sol → high, astra → medium, others max(default, medium); `low` → `medium` with a note; unsupported → highest supported (not `ultra`) with a note; `ultra` only on explicit request.
3. **F9.** A model token with shell metacharacters is rejected with zero `codex` calls (mcp and exec); resolved slugs match `^[A-Za-z0-9._-]+$`.
4. **Override scope (eval-provable part).** Without `AskUserQuestion` a differing choice applies to this consultation only and the reply says so; re-stating the session setting asks nothing and adds no note; a session-scoped choice stated earlier is used later. The interactive `AskUserQuestion` scope question is moved to ticket 09 (recorded) and is **not** part of this claim.
5. **Evidence validity and safety.** The Codex-home probe shows seeding reaches the eval's throwaway home; every ticket-03 scaffold refuses a HOME without `claude-eval` before writing; the operator's real `~/.codex` is untouched; the offline check (`node evals/_harness/ticket03-patterns.test.mjs`) passes, including the reference model-token rule reproducing every case's reading.

## Evidence locations

- `skills/ask/SKILL.md` (step 0 "Model and effort", step 6, step 10 line 1).
- Cases (tag `ticket-03`) under `evals/`: alias-sol, alias-astra, alias-sol-low, alias-ambiguous, alias-unknown, alias-metachar, effort-unsupported, default-model-config, session-override-persists, override-restated-no-prompt, codex-home-probe; regression `manual-with-question`.
- `evals/_harness/model-token-rule.mjs`, `evals/_harness/ticket03-patterns.test.mjs`.
- Eval results under `evals/results/` from 2026-09-15T12-46 onward (all with the Bash/Write grant) and ticket 03 Comments.

## Allowed reproduction

Static reading; `claude plugin validate`; the offline checks; git inspection; stub probes in a temp dir under `D:\tmp` (delete afterwards). Do not run the real Codex CLI or the paid eval suite. Do not write under the operator's `~/.codex` (WSL `/home/cbc/.codex` or Windows `D:\codex`).

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-claim findings (P0–P4) and evidence.
