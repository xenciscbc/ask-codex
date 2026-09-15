# Verifier brief — ticket 01 (boundary 1)

Repo: `D:\work_data\project\skill\ask-codex`, branch `design/ask-codex-mvp`, ticket-01 implementation commit (hash given in the Agent prompt).
Approved Plan: `R:\Temp\claude\D--work-data-project-skill-ask-codex\36c44f16-0840-4987-8e42-582b970b27ca\scratchpad\plan\PLAN.md` (sections "MCP policy", "F-map", "Slice 01").
Ticket: `.scratch/ask-codex-mvp/issues/01-manual-consultation-tracer-bullet.md` (acceptance + Comments with recorded live evidence).
Spec: `.scratch/ask-codex-mvp/spec.md`; ADR-0003: `docs/adr/0003-mcp-policy.md`.

## Exact claim to confirm or refute

The ticket-01 implementation of the `ask-codex:ask` skill satisfies these F-map rows (01 parts):

- **F1-core** — default MCP policy disables every listed MCP server per consultation via same-name disabled definitions, and an MCP guard (re-listing with the overrides) aborts before any `codex exec` when a server is still enabled.
- **F1-apps** — `--disable apps` is always passed (live-verified to remove `mcp__codex_apps`).
- **F1-claims (docs + skill text)** — spec/tickets carry no unconditional read-only claim (doc check), and `skills/ask/SKILL.md` contains the narrowed claim verbatim.
- **F2** — the exec contract keeps `-s read-only`; shell network was live-verified blocked.
- **F3-secrets (template)** — `skills/ask/prompts/consultation.md` instructs Codex to stay in scope, never read in-project secrets, use MCP for lookups only, and treat content as data.
- **F6** — the stub validates exec argv against an allowlist and records violations; graders require stub records per case.
- **F7** — the runner drops PATH entries holding a real `codex` and refuses to run unless `codex` resolves to the stub.
- **F8 (temp dir)** — temp dir via `mktemp -d` under an `ask-codex` parent whose path means the same place to Bash and to the file tools (on Windows converted with `cygpath -m`; never a bare `/tmp` there); removal only of a literal path containing `/ask-codex/`; cleanup mandatory before the final answer.
- **F9 (01 part)** — model slug and server names validated against `^[A-Za-z0-9._-]+$`; effort from a fixed enum; all paths literal and single-quoted; no shell variables or multi-line `codex` commands; no `cd` (commands in other directories use `env -C '<dir>' …` / `git -C`).
- **No-retry rule** — a `codex exec` may be re-run only when it failed from Claude's own invocation mistake before Codex started; never after Codex started (answered, failed, or timed out).
- **F12b (01 part)** — project-only / redefined servers end up in the disable set; a project-layer `.codex/config.toml` MCP definition (project dir up to repo root) aborts before any `codex` call.

## Evidence locations

- Skill: `skills/ask/SKILL.md`, `skills/ask/consultation.schema.json`, `skills/ask/prompts/consultation.md`.
- Harness: `evals/_harness/run-evals.sh`, `evals/_harness/stub/codex`, `evals/_harness/stub/codex-stub.py`, `evals/_harness/codex-call-regex.test.mjs`.
- Eval cases (tag `ticket-01`): `evals/manual-with-question`, `evals/mcp-guard-blocks`, `evals/project-defined-server`, `evals/project-layer-aborts-01` (graders under each `graders/`).
- Live evidence: ticket 01 `## Comments` (live calls 1–3, listing facts, eval iterations).

## Cheap reproduction (allowed)

- `node evals/_harness/codex-call-regex.test.mjs` → PASS.
- `claude plugin validate .` → passes.
- Read the stub and runner and check the allowlist/PATH logic against F6/F7.
- Re-running the eval suite costs money (runs inside WSL: `wsl.exe -d Ubuntu -e bash -lc 'cd /mnt/d/work_data/project/skill/ask-codex && bash evals/_harness/run-evals.sh --tag ticket-01 --runs 1 --model claude-sonnet-5 --max-cost-usd 3 --allow-tools Bash Write'`); do so only if static evidence is insufficient, at most once. Do not run the real Codex CLI.

## Output

CONFIRMED / REFUTED / INCONCLUSIVE per the role contract, with per-row findings (P0–P4) and evidence.
