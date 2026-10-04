# 02 — `/ask-codex:discuss rounds <n> <topic>` runs a discussion end to end

**What to build:** the user types `/ask-codex:discuss rounds <n> <topic>` (optionally with one model token) and gets a complete discussion. Claude frames the topic, writes its own complete round-1 result to a temp file, and only then starts Codex on a blind round 1 (topic and context, never Claude's result). Claude integrates both results into tentative agreements and contested points (ids `L…` for Claude-raised, `C…` for Codex-raised), runs rounds 2..n in fresh sessions carrying only contested points with both sides' full reasons, evidence and prior stances, and stops early when nothing is contested or at the limit. The report is in the conversation: process summary, agreed list, user decision items with both sides' recommendation and reason. The skill is user-only; `ask` points discussion requests to the command. Core of Plan slice S2 (spec: Solution, Implementation Decisions; user stories 1–5, 7, 10–24, 32–41, 43, 47–51).

**Blocked by:** 01 — Script selects the discussion reply schema; stub answers per round.

**Status:** resolved — eba3939 + 2e970b8 + grader fix (2026-10-05); see Comments

- [ ] The skill cannot be invoked by the model; the plugin's skills list includes it; `ask` has a pointer line for multi-round discussion requests.
- [ ] Model token resolved once through `ask`'s resolve step and fixed for every round; two model tokens are refused before any Codex call.
- [ ] Every round's request selects the discussion reply schema and goes through `ask`'s unchanged execution operations (prepare/MCP guard every round, wait, stop, collect).
- [ ] Discussion prompt template repeats `ask`'s rules 1–3 word for word (offline drift test); round-1 and round-n framings each carry a unique marker line.
- [ ] Missing topic → inferred from the conversation and disclosed; nothing inferable → ask and stop before any Codex call.
- [ ] Temp files (Claude's round-1 result, prompts, requests) are in the scratch location and deleted after the report; nothing is written into the project.
- [ ] Eval `discuss-early-consensus` (`rounds 5`, round 2 accepts everything): exactly 2 calls, both with the discussion schema; round 2 prompt has the round-n marker, every carried id and a round-1 Codex reason verbatim; report has the three sections.
- [ ] Eval `discuss-limit-reached` (`rounds 2`, a point maintained): exactly 2 calls; that point is a user decision item with both recommendations.
- [ ] Eval `discuss-claude-first`: the Write of Claude's round-1 file precedes the first `run` operation in the trace; the round-1 prompt has the round-1 marker and no carried-points section.
- [ ] Eval `discuss-rounds-arg-no-question`: `rounds 2` → no `AskUserQuestion` tool use.
- [ ] Eval `discuss-two-models-refused`: no Codex call.
- [ ] Evals `discuss-nl-not-loaded` and `discuss-not-model-invocable` pass at `--runs 5` (body marker never in the trace, no discuss framing marker sent; natural-language case's final message names `/ask-codex:discuss`).
- [ ] Other cases pass at `--runs 3`; offline harness tests pass (CRLF exception as in 01).
- [ ] Regression: `second-opinion-with-stance`, `targeted-check`, `review-working-tree` at `--runs 3` on baseline `6266c3e` and on this ticket's commit; no grader's pass rate drops (pre-existing stale graders fail equally and do not block).
- [ ] One-off: with model invocation re-enabled locally (never committed), `discuss-nl-not-loaded` fails at least once in `--runs 5`.

## Comments

- 2026-10-05 — Implemented by executor (eba3939); main-session review changed one rule before evals: points both sides drop are listed under `Agreed` as `(dropped)`.
- t02 on eba3939 (`evidence/t02-run-log.txt`): two-models 3/3, rounds-arg 3/3, claude-first 3/3, limit-reached 3/3, not-model-invocable 5/5. Failures diagnosed:
  - early-consensus run kept a point contested after Codex returned `accept` with a thin reason, split one id into parts and ran 5 rounds — skill defect, fixed in 2e970b8 (a returned stance always takes effect; a partly agreed point is contested whole, never split).
  - `temp-file-deleted` grader: `\brm\b` misses `rm` after a literal `\n` in a multi-line command; `round-2-reason-verbatim`: lower-case first letter. Grader false fails, fixed with offline proofs.
  - nl-not-loaded `names-command` 3/5: the prompt said "this design" with no design in context, so Claude asked which design without loading `ask`. Fixture defect; the prompt now names src/login.js and docs/constraints.md.
- t02b on 2e970b8 (`evidence/t02b-run-log.txt`): early-consensus 3/3 except one `no-bare-cd` (a `cd <scratch> && python3 -c` — pre-existing model habit also seen in `ask` and `review`, named P3 residual, not introduced here); limit-reached 2/3 + one `c3-decision-item` false fail (the reply named C3 inside its own recommendation; grader now excludes only other C ids, offline-proven on all six real replies); claude-first, rounds-arg, two-models 3/3; nl-not-loaded 5/5.
- One-off detection (`evidence/noflag-run-log.txt`): with `disable-model-invocation` removed in a worktree (never committed), nl-not-loaded failed 5/5 (skill body loaded, discussion framing sent).
- Regression vs 6266c3e (`evidence/baseline-run-log.txt`, `t02-run-log.txt`): review-working-tree 3/3 both; second-opinion-with-stance and targeted-check carry the stale ticket-09 graders equally; targeted-check `concern-sent` strict 2/3 fail vs 1/3 at baseline, but the backtick-tolerant match finds the concern in 3/3 on both (known since codex-review); second-opinion `no-bare-cd` 1/3 vs 0/3 — the same pre-existing habit. No grader pass rate drops beyond these named, pre-existing patterns.
