# ask-codex MVP — plan artifacts

Copied from the implementing session's scratchpad (`R:\Temp\claude\…\scratchpad\plan\`, a RAM disk) on 2026-09-16 so they survive a reboot. They are working documents, not product docs.

- `PLAN.md` — program envelope: execution order, MCP policy, F-map (security dispositions → ticket → acceptance), eval run settings, budget decisions, deferred items and lessons, stop conditions.
- `slice-*.md` — per-ticket execution contracts, each with its readiness record (plan-verifier rounds and dispositions).
- `verifier-*-brief.md` — briefs given to the outcome verifiers.
- `gen-ticket*-cases.mjs` — generators that wrote the eval cases under `evals/` (rerun one to regenerate its ticket's cases). `gen-ticket07-probe.mjs` writes the ticket-07 tool probe.
- `t03-fixture/` — the ticket-03 Codex-home fixture (reduced model cache, config) and the reference model-token rule; `ticket02-history.jsonl` — the ticket-02 conversation fixture.
- `summarize-eval.mjs`, `check-*.mjs`, `win-stub-run.sh`, `live-11.sh` — helper scripts (the live script belongs to ticket 11's live check).
- `ask-skill-t*.md`, `stub-t*-draft.py`, `consultation-t02-insert.md`, `t06-drafts/`, `notes-*.md` — drafts and notes written while implementing; the committed skill and stub are authoritative.
- `t04-evidence.json` — recorded final replies used to build ticket 04's grader test.

Paths inside these files still point at the original scratchpad (`R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-…\scratchpad\plan\`) and at `D:\work_data\project\skill\ask-codex`; read them as "this directory" and "the repository root". Decisions and evidence for each ticket are also recorded in the ticket Comments under `../issues/`.
