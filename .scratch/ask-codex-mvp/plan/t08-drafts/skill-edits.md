Ticket-08 SKILL.md edits (apply after the red runs):

1. Ground rules — "No retries once Codex has started": "… once Codex has started — whether it answered, failed, or timed out — never run it again for the same consultation (in a parallel consultation: for the same model)."
2. Failures — "Run `codex exec` at most once per consultation" → "at most once per consultation and model".
3. Step 0 — after item 2 of Model and effort:
   **Two models (parallel).** If the start of the request lists two model tokens separated by a comma (each may carry `:<effort>`), resolve and validate each as above; each gets its own effort. More than two models, or the same model twice after resolution, → write `Parallel consultation takes at most two different models.` and stop — no temp dir, no `codex` command. A token that fails validation stops the consultation as in item 3. Proactive consultations run in parallel only when the session setting names two models.
4. Steps 1, 7, 8, 9, 11 — for a parallel consultation:
   - Step 1: create one run directory per model (`mktemp -d` twice); steps 2–5 run once (same policy, disable set and guard for both).
   - Step 7: write the same `prompt.md` into each run directory.
   - Step 8: start one background `codex exec` per model (its own `-m`, effort, `-o` and output files), all with the full disable set; one shared timer. At each check write `Parallel check: done — <slugs or none>; still running — <slugs>.` and apply the liveness rules only to runs still going (ask or, without `AskUserQuestion`, stop them). Hold finished results — present nothing until every run has finished or been stopped.
   - Step 9: read each run's reply; then clean up both run directories.
   - Step 11: remove every run directory.
5. Step 10 — **Parallel reply.** Item 1 names both models and efforts; restate each `Parallel check:` line word for word. Then the headings `Consensus`, `Solo claims`, `Divergences`; tag each claim `[gpt-…]` (or `[both]`) and give a disposition; end each divergence with `Adopted: <slug> — <reason>`. If one run failed or was stopped: present the other normally (no grouping) and add `Failed model: <slug> — <reason>` (a stop: `Failed model: <slug> — stopped after <elapsed> without progress`); attribute nothing to the failed model.
