# Verifier brief — ticket 08 (parallel consultation)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`; candidate = the commit titled "Ticket 08: parallel consultation" (resolve with `git log --oneline -5`; it follows `d8102ca`).
Execution contract: `.scratch/ask-codex-mvp/plan/slice-08.md` (revision 2, READY). Envelope / lessons: `.scratch/ask-codex-mvp/plan/PLAN.md`.
Ticket: `.scratch/ask-codex-mvp/issues/08-parallel-consultation.md` (criteria + Comments: readiness, entry gate, stub and reference rule, red, green).

## Execution facts to check against

- Red (ticket-06 skill): all three red cases failed on the new behaviour (the old skill improvised two runs but had no merged format; no fixed refusal line; no consultation in the partial-failure case).
- First green: 4/7; three wording misses with correct behaviour (alias tags `[astra]` instead of full slugs; bold `**Failed model:**` splitting the fixed words; no restated `Parallel check:` line — the kept transcript showed the check described in prose, and no claim before the final reply). Fixes: full slugs in tags; plain-text `Failed model:` / `Parallel check:` lines; the check line on its own line in step 8 and restated in item 1; the regexes tolerate markdown around the fixed words, not a different model or order (offline samples added).
- All seven cases were then rerun on the final bytes; case 5 was kept again and its excerpt rewritten to `.scratch/ask-codex-mvp/evidence/parallel-shared-timer.txt` — check timestamps against the last SKILL.md edit and the commit.

## Exact claim to confirm or refute

1. **Two models, refusals.** A request starting with two comma-separated models (optional `:effort` each) runs a parallel consultation; each model resolves by ticket 03's rules with its own effort. Three models or the same model twice → `Parallel consultation takes at most two different models.` and no `codex` command; a listed token with metacharacters → invalid, no `codex` command.
2. **Independent runs with the full contract.** One background `codex exec` per model in its own temp dir, identical prompt, neither prompt containing the other's reply; every run carries the full MCP disable set, `-s read-only` and `--disable apps` (per-model argv graders), no stub violations; "one exec per consultation" is per model, no retries.
3. **Shared timer.** One interval; at a check the fixed `Parallel check: done — …; still running — …` line; only running models are asked about / stopped; no claim shown before every run has finished or been stopped (read the committed transcript excerpt `.scratch/ask-codex-mvp/evidence/parallel-shared-timer.txt`).
4. **Presentation.** Merged reply with `Consensus`, `Solo claims`, `Divergences`, model tags, dispositions and `Adopted: <slug> — <reason>` per divergence; partial failure or stop → survivor presented without grouping plus `Failed model: <slug> — <reason>`, nothing attributed to the failed model.
5. **Evidence validity.** Stub `by_model` and per-model records (`stub-modes.test.mjs`), the extended reference token rule (`model-token-rule.mjs` self-check, `ticket03-patterns.test.mjs`), `ticket08-graders.test.mjs`; red failed on the new behaviour; green ran on the committed skill bytes; ticket-03 regression `alias-sol` and ticket-01 regression pass.
Not in the claim: proactive two-model parallel (written only; ticket 05 paused).

## Allowed reproduction

Static reading; `claude plugin validate`; the offline tests; git inspection; stub probes in a temp dir under `D:\tmp` (delete afterwards). Do not run the real Codex CLI or the paid eval suite.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-claim findings (P0–P4) and evidence.
