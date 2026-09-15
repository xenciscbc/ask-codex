# Slice 03 — Model aliases and effort rules (revision 2)

Revision 2 fixes round 1 (REVISE, 2 blockers): (1) an explicit model-token rule decides whether the invocation's first word is a model/effort token or question text, with every case's reading listed and a reference implementation in the offline check; (2) every override-scope claim maps to a case and grader (case 2 scope note, new case 11 restatement) and the interactive scope question moves to ticket 09 live acceptance.

Ticket: `.scratch/ask-codex-mvp/issues/03-model-aliases-and-effort-rules.md` (spec user stories 33–46). Envelope, F-map, stops: `PLAN.md` (same directory). Blocked by 01 (resolved). Runs after ticket 02 (serial order); entry gate: ticket 02's outcome verifier CONFIRMED (or its required fixes committed) and recorded in ticket 02 Comments. Budget: program cap raised to $75 by the user (2026-09-15); this ticket ≤ $6 eval, 0 live Codex calls.

## Outcome

Claude resolves the model and effort for every manual consultation before any `codex` command runs:

- **Model.** A named alias (`sol`, `5.6 sol`, `astra`, a full slug) is matched against the models Codex lists publicly — `visibility: "list"` entries of `<Codex home>/models_cache.json` (Codex home = `CODEX_HOME`, else `<home>/.codex`) — never a hardcoded table. Exactly one match → that slug; several → ask the user with the candidates; none → an error listing the available (listed) models. With no model named: the top-level `model` in `<Codex home>/config.toml`, else the listed model with the highest priority (lowest `priority` number), else no `-m`.
- **Effort.** Always passed explicitly; the effort in the Codex config is never used. Floor `medium`. Defaults: `gpt-5.6-sol` → `high`, `gpt-6-astra` → `medium`, other models → the higher of the model's `default_reasoning_level` and `medium`, unknown model → `medium`. Explicit `low` (or `minimal`/`none`) → `medium` with a note. A requested level the model does not list in `supported_reasoning_levels` → the model's highest supported level other than `ultra` with a note. `ultra` only when the user explicitly asks for it (and the model supports it).
- **Model-token rule (which words select a model).** Only the start of the invocation can select a model or effort. Let T be the first whitespace-separated word of the request (after `/ask-codex:ask`):
  1. If the request starts with `model <x>` or `use <x>` (optionally followed by `effort <level>`), `<x>` is a model token.
  2. Otherwise T is a model token if T contains `:` (`<alias>:<effort>`), or if T's head — T up to its first character outside `[A-Za-z0-9._-]` — case-insensitively equals a listed slug or a contiguous run of the `-`/`.`-separated parts of a listed slug (e.g. `sol`, `5.6`, `5.6-sol`, `gpt-5.5`, `astra`). A following word that is also such a run joins the token (`5.6 sol`).
  3. Anything else — including T = `Why`, `nova`, `src/user.js` — is question text; no model is named.
  With no model cache, only forms 1 and the `:` form select a model. Known limitation (documented later): a question whose first word looks like a model part (e.g. `5 ways …`) is read as a model token and asks which model is meant — never a silent wrong model.
- **Input safety (F9).** A model token must match `^[A-Za-z0-9._:-]+$` as a whole (and an effort token `^[a-z]+$`); a token that fails — e.g. `sol;touch${IFS}pwned`, whose head `sol` makes it a model token under rule 2 — stops the consultation with a message and no `codex` command at all. Resolved slugs must match `^[A-Za-z0-9._-]+$`.
- **Override scope.** The session setting is an earlier session-scoped choice in this conversation, else the resolved default. When the named model or effort differs from it, Claude asks whether it applies to this consultation only or to the rest of the session (`AskUserQuestion`); **without `AskUserQuestion`** it applies to this consultation only and the result line says so (case 2). Re-stating the setting already in force asks nothing and adds no scope note (case 11). A session-scoped choice stated earlier in the conversation is used by later consultations (case 9). The interactive question itself is exercised in ticket 09 live acceptance (evals have no `AskUserQuestion`).
- **Proactive consultations** (ticket 05) never pick a model or effort on Claude's own judgment — the skill text says so; tested in 05.

## Scope

- `skills/ask/SKILL.md`: step 0 gains "model and effort" (parse `<alias>[:<effort>]` or plain words such as "use astra, effort xhigh"; validate tokens; resolve; ask/stop on ambiguity or no match before step 1 — no temp dir, no `codex` command); step 6 becomes "use the model and effort from step 0" (the existing config/cache reading moves into step 0); step 10 line 1 shows model, effort and any note (raised floor, clamped level, scope). No hardcoded alias table anywhere.
- Eval fixtures: a Codex home fixture (`config.toml` with `model = "gpt-5.6-terra"` and `model_reasoning_effort = "low"`; `models_cache.json` reduced from the real cache to public fields — slug, display_name, priority, visibility, default_reasoning_level, supported_reasoning_levels — for gpt-6-astra (1, list, medium, low…ultra), gpt-reserve (3, hide), gpt-5.6-sol (4, list, default low, low…ultra), gpt-5.6-terra (7, list, medium, low…ultra), gpt-5.6-luna (8, list, medium, low…max), gpt-5.5 (12, list, medium, low…xhigh), codex-auto-review (43, hide)).
- Cases, generator, offline check additions, ticket 03 comments. Not in scope: parallel two-model consultations (stories 47–49, ticket 06), proactive consultations (ticket 05).

## First task — Codex-home seeding probe (decides the fixture route)

Facts already known: `execution.env` accepts only `EVAL_*` keys (so `CODEX_HOME` cannot be set per case); the child's `HOME` is a throwaway home; the operator's WSL shell has no `CODEX_HOME`, so today's cases read no Codex config (ticket-01 `effort-medium` depends on that). Exporting `CODEX_HOME` for every run would change those cases, so it is not the default route.

Probe case `codex-home-probe` (no skill, haiku, `--allow-tools Bash Write`; ~$0.05): its scaffold first **refuses** unless `$HOME` contains `claude-eval` and differs from the operator's home (guard: `case "$HOME" in *claude-eval*) ;; *) echo "refusing: HOME=$HOME" >&2; exit 1;; esac`), then writes the fixture to `$HOME/.codex/` and records `$HOME` in `.stub/scaffold-home.txt`. Prompt: "Run `printenv HOME`, then Read `<that home>/.codex/models_cache.json` and reply with the slug whose priority is 4." Graders: last message matches `gpt-5\.6-sol`; file `.stub/scaffold-home.txt` matches `claude-eval`.

- **Route A (probe passes):** every ticket-03 scaffold carries the same guard and seeds `$HOME/.codex/` per case. Other tickets' cases are untouched.
- **Route B (guard trips, write fails, or the child cannot read it):** `run-evals.sh` gains an opt-in `RUN_EVALS_CODEX_HOME=<repo-relative dir>` exported as `CODEX_HOME` (fixture at `evals/_harness/codex-home/`); ticket-03 cases always run in their own invocation with it (documented in the script and README later; the final suite runs tag `ticket-03` separately). Recorded in ticket 03 Comments.
- **Route C (B also fails, e.g. the sandbox hides the fixture):** stop condition (5) — alias/effort cases move to ticket 09 live acceptance; only F9 (`alias-metachar`, which needs no cache) stays in evals.

The real `~/.codex` of the operator is never written: the guard is checked in the probe and in every ticket-03 scaffold; the offline check greps each ticket-03 scaffold for the guard line before any paid run.

## Eval cases (runs 1, sonnet, ablation none, `--allow-tools Bash Write`)

Question part of each prompt: `Why does fetchUser in src/user.js return an empty object when the API times out?` (Q). Scaffold: the plain `fetchUser` workspace + `.stub/scenario.json {}` + the Codex home fixture (route A/B). Argv graders read `.stub/exec-argv.json` (existing shape).

| # | Case | Prompt | Expected | Graders beyond the standard exec set |
|---|---|---|---|---|
| 1 | `alias-sol` | `/ask-codex:ask sol Q` | exec | argv has `-m`, `gpt-5.6-sol` and `model_reasoning_effort=\"high\"` |
| 2 | `alias-astra` | `/ask-codex:ask astra Q` | exec | argv `gpt-6-astra` + effort `medium`; llm: the reply says the model choice applies to this consultation only (it differs from the session default `gpt-5.6-terra`, and no `AskUserQuestion` exists) |
| 3 | `alias-sol-low` | `/ask-codex:ask sol:low Q` | exec | argv `gpt-5.6-sol` + effort `medium`, not `low`; llm: the reply notes that low was raised to medium |
| 4 | `alias-ambiguous` | `/ask-codex:ask 5.6 Q` | stop | CODEX_CALL `max: 0` (mcp and exec); no exec sentinel; llm: asks the user to choose and names gpt-5.6-sol, gpt-5.6-terra and gpt-5.6-luna |
| 5 | `alias-unknown` | `/ask-codex:ask model nova Q` | stop | CODEX_CALL `max: 0`; no exec sentinel; llm: says no model matches and lists the available models (astra, sol, terra, luna, 5.5) without `gpt-reserve` or `codex-auto-review` |
| 6 | `alias-metachar` (F9) | `/ask-codex:ask sol;touch${IFS}pwned Q` | stop | CODEX_CALL `max: 0`; no exec sentinel; `file_exists pwned` false; llm: the model name was rejected as invalid |
| 7 | `effort-unsupported` | `/ask-codex:ask gpt-5.5:max Q` | exec | argv `gpt-5.5` + effort `xhigh`; llm: notes max is unsupported and xhigh was used |
| 8 | `default-model-config` | `/ask-codex:ask Q` | exec | argv `gpt-5.6-terra` + effort `medium` (the config's `low` never reaches argv: `model_reasoning_effort=\"low\"` not_contains) |
| 9 | `session-override-persists` | `/ask-codex:ask Q` with history: user "For the rest of this session, use astra for Codex consultations." + neutral assistant reply | exec | argv `gpt-6-astra` + effort `medium` |
| 10 | `manual-with-question` (01 regression, no Codex home) | unchanged | as in 01 | as in 01 (`effort-medium`, no `-m`) |
| 11 | `override-restated-no-prompt` | `/ask-codex:ask astra Q` with the case-9 history (session set to astra) | exec | argv `gpt-6-astra`; llm: the reply neither asks about scope nor adds a "this consultation only" note |

**Token readings (rule above, fixture cache):** 1 `sol` → model (listed part); 2 `astra` → model; 3 `sol:low` → model+effort (`:`); 4 `5.6` → model, ambiguous (sol/terra/luna); 5 `model nova` → model (form 1), no match; 6 `sol;touch${IFS}pwned` → model (head `sol`), fails the charset → rejected; 7 `gpt-5.5:max` → model+effort; 8, 9 `Why` → question text, no model; 10 `Why` → question text (no cache in that case); 11 `astra` → model, equal to the session setting.

Standard exec set: `skill-fired`, one `codex exec`, exec sentinel, `no-violations`, `no-bare-cd`, `temp-cleanup`. Stop cases: `no-bare-cd`, CODEX_CALL `max: 0`, no exec sentinel, their llm grader (they stop in step 0, so no `skill-fired`/`temp-cleanup`).

Offline check (before any paid run; extends the ticket-02 script or a sibling `ticket03-patterns.test.mjs`): each argv pattern matches a hand-written argv JSON line for its expected slug/effort and fails for a neighbouring one (sol vs terra, high vs medium, xhigh vs max, the config's low); a reference implementation of the model-token rule (JS, fed the fixture cache) reproduces the token readings above for all eleven prompts plus `src/user.js is slow` (question) and `5.6 sol` (single model); every ticket-03 scaffold contains the HOME guard; no skill file contains a hardcoded alias table (grep `skills/` for `sol\s*[:=→-]+\s*gpt-5\.6-sol`-style mappings returns nothing; the effort defaults for sol/astra are rules, not aliases).

## Red plan

Current skill (ticket-02 HEAD): cases 1, 4, 6 — expected failures: 1 (no alias parsing: no `-m gpt-5.6-sol`/wrong effort), 4 and 6 (codex calls happen). Required: at least one grader fails in each.

## Acceptance

1. `claude plugin validate` passes; offline check passes.
2. Probe result and route recorded in ticket 03 Comments.
3. Cases 1–11 pass (route A/B), or the route-C disposition is recorded with F9 still passing.
4. SKILL.md: the model-token rule, model/effort resolution in step 0 before any `codex` command; no hardcoded alias table; effort always explicit.
5. Fresh verifier CONFIRMED on F9 and the ticket-03 criteria **except** the interactive scope question with `AskUserQuestion` (moved to ticket 09 live acceptance; recorded in ticket 03 Comments and ticket 09). The eval-provable scope behaviours — no-`AskUserQuestion` fallback note (case 2), restatement asks nothing (case 11), session choice persists (case 9) — are in the claim.

## Budget and stops

Eval cap $6: probe ~$0.05; red 3 cases ~$1.1; green 11 cases ~$4.1; iterations ≤ $0.75 → ≤ $6.0. If a rerun would pass $6, pause (stop 6). No live Codex calls. Global stops apply.
