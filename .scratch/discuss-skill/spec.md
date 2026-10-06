# Spec: ask-codex discuss skill

Status: resolved on branch `feat/discuss-skill` (2026-10-06) — not merged, tagged or pushed; see Outcome at the end.

Vocabulary follows `CONTEXT.md` (section 討論, added 2026-10-04 during the grilling session). Decisions respect ADR-0001 (call `codex exec` directly), ADR-0002 (fresh session per follow-up), ADR-0003 (MCP policy), ADR-0005 (script-owned execution) and ADR-0006 (user-only review skill pattern). A new ADR-0007 records the discuss skill and why a multi-round discussion still uses a fresh Codex session per round.

Tickets: `issues/01` … `issues/06` (ticket ↔ Plan slice mapping in each ticket).

## Problem Statement

When I design something with Claude — a feature, an interface, a workflow — I want a second, independent mind on it, and I want the two of them to actually work the disagreements out. `/ask-codex:ask` gets one opinion per call: Claude judges Codex's claims, but Codex never answers Claude's objections, and Claude's own ideas are never challenged by Codex unless Claude reveals its stance, which anchors the answer. Running several `ask` follow-ups by hand loses track of what is already agreed, what is still disputed and who was persuaded by what. At the end I get a pile of claims and dispositions instead of what I need: what is settled, and which questions only I can decide, with each side's recommendation and reason.

## Solution

A new user-only command, `/ask-codex:discuss [model token] [rounds <n>] [topic]`. Claude frames the topic and context. In round 1, Claude and Codex each produce their own result independently — Claude writes its result down before Codex starts, and Codex never sees it. Claude then integrates both: points both raised become tentative agreements; Codex's own points that Claude agrees with join them; Codex's points Claude disputes, and Claude's own points, become contested points for the next round. Each later round sends only the contested points, with both sides' full reasons and evidence, to a fresh Codex session; Codex accepts, maintains or revises each, and Claude answers in turn. The discussion ends when nothing is contested or the round limit (chosen by me when I start it) is reached. Claude then reports a short process summary, the agreed list, and the user decision items, each with both sides' recommendation and reason. Codex stays read-only throughout, under the same MCP policy as `ask`.

## User Stories

1. As a developer, I want to start a discussion with Codex by typing `/ask-codex:discuss <topic>`, so that a design question gets worked out by two independent agents rather than one.
2. As a developer, I want only my typed command to start a discussion, so that Claude, files, tool results or Codex output can never start a multi-round, multi-call discussion on their own.
3. As a developer, I want a natural-language request like "discuss this with Codex over a few rounds" to be answered with a pointer to `/ask-codex:discuss` rather than silently starting one, so that I stay in control of a costly operation.
4. As a developer, I want `ask` to point me to `/ask-codex:discuss` when I ask it for a multi-round discussion, so that I learn the right tool exists.
5. As a developer, I want one command to authorize every round up to the limit, so that I am not interrupted between rounds.
6. As a developer, I want to be asked how many rounds to allow — 3, 5, 7 or my own number — when I start a discussion without saying, so that I control cost and depth.
7. As a developer, I want to put `rounds <n>` in the command and not be asked, so that I can start a discussion in one line.
8. As a developer, I want a custom round count outside 2–10 to be refused and asked again, so that I cannot start a pointless one-round discussion or an hours-long one by mistake.
9. As a developer running headless, I want a discussion without a round count to use 3 rounds and say so in the report, so that unattended runs are bounded and transparent.
10. As a developer, I want to name the Codex model (and effort) the same way as in `ask`, so that I do not learn a second syntax.
11. As a developer, I want the model and effort fixed for the whole discussion, so that agreements are not reached with one model and overturned by another.
12. As a developer, I want naming two models to be refused with a reason, so that I do not mistake a discussion for a parallel consultation.
13. As a developer, I want Claude to infer the topic from our conversation when I give none, and tell me what it inferred, so that I can start a discussion right where we are.
14. As a developer, I want Claude to ask and stop when no topic can be inferred, so that no Codex call is wasted on a guess.
15. As a developer, I want Codex's round 1 to receive the topic and context but never Claude's answer, so that Codex's view is not anchored by Claude's.
16. As a developer, I want Claude to write its complete round-1 result down before Codex starts, so that Claude's view is not anchored by Codex's either.
17. As a developer, I want Claude to integrate from that written result without rewriting it, so that the comparison between the two independent views is honest.
18. As a developer, I want points both sides raised to become tentative agreements immediately, so that later rounds focus on real disagreements.
19. As a developer, I want Codex's own points that Claude agrees with to join the tentative agreements, so that good ideas from Codex are kept without debate.
20. As a developer, I want Codex's points Claude disputes, together with Claude's own points Codex has not yet weighed in on, carried into the next round as contested points, so that every claim is tested by the other side.
21. As a developer, I want each discussion point labelled with who raised it and a stable id, so that I can follow a point across rounds.
22. As a developer, I want every round to carry both sides' full reasons and evidence for each contested point, so that the fresh Codex session judges arguments, not summaries.
23. As a developer, I want Codex to answer each contested point with accept, maintain or revise (with a proposed wording), so that the state of every point is unambiguous.
24. As a developer, I want Claude to answer Codex's stances in turn, with the same three choices, so that both sides are held to the same standard.
25. As a developer, I want a concession to cite specific evidence — a file location, a document, a counter-example — so that a side is persuaded by facts, not by pressure.
26. As a developer, I want a concession without such evidence reported as an unevidenced concession, so that I can discount it.
27. As a developer, I want Codex told to answer "maintain" when it has no new substantive argument, so that rounds do not fill up with invented objections.
28. As a developer, I want points that flip in round 3 or later flagged in the report, so that I treat late convergence with suspicion.
29. As a developer, I want new points after round 1 allowed only when they would change the conclusion, and marked as such, so that a discussion converges instead of growing.
30. As a developer, I want tentative agreements locked in later rounds, reopenable only when a contested point decided in that round affects them, so that settled ground is not relitigated without cause.
31. As a developer, I want either side to be able to mark a point as a matter of my preference or authority rather than right or wrong, and once both do, to stop debating it and hand it to me, so that rounds are not spent on what only I can decide.
32. As a developer, I want the discussion to stop early once nothing is contested, so that I do not pay for rounds that cannot change anything.
33. As a developer, I want contested points still open at the round limit handed to me as user decision items, so that nothing is silently dropped.
34. As a developer, I want each user decision item to show both sides' recommendation and reason, merged when they agree, so that I can decide quickly.
35. As a developer, I want the report to start with a short process summary — one or two lines per round, who was persuaded by which argument — so that I can trust how the result was reached.
36. As a developer, I want a clear agreed list, so that I can act on it.
37. As a developer, I want the report in the conversation only, never written into my project, so that a discussion leaves no files behind.
38. As a developer, I want each round to run in a fresh Codex session, so that the read-only guarantee holds (resume cannot take the sandbox flag) and Codex is not anchored on its own earlier turn.
39. As a developer, I want Codex read-only in every round, under the same MCP policy and guard as `ask`, so that a discussion never gets wider permissions than a consultation.
40. As a developer, I want the MCP guard to run before every round, so that a configuration change mid-discussion cannot slip through.
41. As a developer, I want confirmations I already gave reused across rounds while the definitions are unchanged, so that I am not asked the same thing repeatedly.
42. As a developer, I want a new confirmation needed mid-discussion asked of me interactively, or, when headless, the discussion ended with the pending item reported, so that nothing runs without my consent.
43. As a developer, I want to be told I can open documentation MCP servers with `/ask-codex:setup` when a topic needs outside documentation, so that I know how to give Codex more to read without widening anything by default.
44. As a developer, I want a failed or stopped round to end the discussion without retrying, so that a broken run never repeats a billable call.
45. As a developer, I want the partial report after an early end to mark which round did not complete and why, and to list open points as "unresolved because the discussion ended", so that I do not confuse an interrupted discussion with a real disagreement.
46. As a developer, I want an unstructured Codex reply to end the discussion with that reply quoted under an explicit unstructured label, so that Claude never invents stances Codex did not give.
47. As a developer, I want the same waiting, liveness check and stop behaviour as `ask` in every round, so that a long round behaves predictably.
48. As a developer, I want Codex's output treated as data in every round, including when it is carried into the next round's prompt, so that text in a reply cannot steer the discussion or Claude's actions.
49. As a developer, I want temporary files (Claude's round-1 result, prompts, requests) deleted after the report, so that project content does not linger in scratch locations.
50. As a developer, I want existing `ask` and `review` consultations to behave exactly as before, so that adding discussions breaks nothing I rely on.
51. As a maintainer, I want the discussion's prompt to repeat `ask`'s read-scope, tool and content-is-data rules word for word, guarded by a test, so that the two cannot drift apart.
52. As a maintainer, I want the README in both languages, the glossary and an ADR to describe the discussion, its honest limits and why it does not resume sessions, so that future readers understand the design.
53. As a maintainer, I want one real harmless discussion with a real Codex model before release, so that the structured-output schema is proven to work outside the stub.

## Implementation Decisions

- **New skill `discuss`, user-only.** Model invocation is disabled, as for `review`: only the typed command loads it. `ask` gains one pointer line for multi-round discussion requests. The plugin's skills list gains `discuss`.
- **Execution reuses `ask`'s script boundary per round.** Each round is one consultation through `consult.py` resolve (once, at the start) → prepare → run → wait → collect, with the existing MCP policy, guard, timer, liveness and stop behaviour. The skill references `ask`'s execution sections rather than duplicating them, as `review` does.
- **One script change: selectable reply schema.** A request may carry `reply_schema` with value `consultation` (default when absent) or `discussion`; any other value is refused before any Codex command. `discussion` requires exactly one model. The prepared summary names the reply schema; run passes the matching schema file to Codex; collect classifies the reply against it. For requests without `reply_schema`, the Codex command line is unchanged.
- **Reply classifier supports booleans.** The schema matcher gains the boolean type; without it, a discussion reply would raise instead of classifying.
- **Discussion reply schema** (type shape; every object node closed with all keys required, as Codex strict structured output requires; nullable fields typed `[<type>, null]`, a nullable enum also lists `null`):

  ```text
  { summary: string,
    points: [ { id: string,                 // Claude-raised L1, L2…; Codex-raised C1, C2…; never renumbered
                statement: string,
                reason: string,             // full reasoning, carried forward verbatim
                evidence: string[],
                kind: "fact" | "inference",
                confidence: "high" | "medium" | "low",
                stance: "accept" | "maintain" | "revise" | null,   // null on a new point
                revised_statement: string | null,                  // with "revise"
                user_call: boolean,          // preference/authority question, not right-or-wrong
                user_call_reason: string | null,
                new_blocking: boolean,       // a new point after round 1
                reopen: boolean } ],         // reopening a tentative agreement
    open_questions: string[] }
  ```

- **Stance vocabulary is independent of who raised the point**: `accept` = accept the other side's position on this point; `maintain`; `revise` = propose a wording both could accept.
- **Round and limit semantics.** A round is one Codex call; round 1 is the independent round. Round limit from `rounds <n>` in the arguments, else an interactive question (3 / 5 / 7 / custom 2–10), else 3 when no interactive tool exists (disclosed). Early stop when no contested point remains.
- **Fresh Codex session every round** (`--ephemeral`, never resume). Sources recorded in ADR-0007: openai/codex#40149 (open; `exec resume` has no sandbox flag and a resumed turn wrote a file read-only had blocked; confirmed locally that resume lacks the flag on 0.159.3), #49078; arXiv 2603.16244 (multi-round review degrades F1 and raises false positives; more carried context helps), 2606.00820 (conformity share of stance flips; vacuous reasoning persuades), 2509.05396.
- **Prompt structure.** The discussion has its own prompt template with `ask`'s rules 1–3 word for word and a discussion answer-format rule; a round-1 framing (topic and context only, blind) and a round-n framing (locked tentative agreements, contested points with both sides' full reasons, evidence and prior stances, the anti-conformity rules, blocking-only new points, reopen rule, user-call marking). Each framing carries a unique marker line for graders.
- **Claude-side rules mirror Codex's.** Claude's concessions need evidence, Claude's late flips are flagged, and Claude's own user-call marks follow the same rule.
- **Early end.** A failed, stopped, unconfirmed-stop or unstructured round, or a headless pending confirmation, ends the discussion with a partial report from the last completed round; no retry.
- **Temporary files** live in the scratch location and are deleted after the report; nothing is written into the project.
- **Release.** Version 1.3.0; README (both languages) gains usage, capability, known risks and a pointer to the MCP policy section and to `codex mcp list` for allowlist names; ADR-0007.

## Testing Decisions

- **Good tests check external behaviour only**: what reaches Codex (prompt and command line, as recorded by the stub), how many Codex calls happen, what the script returns, and what the user sees in the final report — never the skill's internal wording or the order of Claude's private reasoning, except where order is itself the requirement (Claude's round-1 file written before Codex starts).
- **Seam 1 — the `consult.py` command interface with the stub Codex on PATH.** Covers reply-schema selection and refusal, the unchanged command line for existing requests against a literal oracle captured from baseline `6266c3e` with paths normalised (never generated by the new code), classification of discussion replies (valid, and a boolean field of the wrong type) without exceptions, the discussion schema's structural rules, and a full prepare → run → wait → collect discussion run that ends completed and cleaned. Prior art: the existing script tests that drive the operations as subprocesses with the stub on PATH.
- **Seam 2 — the Claude eval harness (real Claude, stub Codex, deterministic graders).** Extended, not new: the stub gains a per-call reply sequence and per-call fixed-path records of each call's prompt and command line, so graders can read round n's prompt and schema. Cases: early consensus, limit reached, Claude-first ordering, headless default, round count in arguments skips the question, out-of-range round count, a failing round, an unstructured round, two models refused, user-call handoff, natural-language request not loading the skill, tool-result instruction not loading the skill. Prior art: the `review-*` and `followup-*` cases and their grader tests.
- **Regression**: `second-opinion-with-stance`, `targeted-check` and `review-working-tree` on baseline and on the change; no grader's pass rate drops. One-off detection proof: with model invocation re-enabled locally (never committed), the natural-language case fails at least once in five runs.
- **Offline invariants**: the discussion prompt's rules 1–3 equal `ask`'s word for word.
- **Live acceptance** (not automated): one real two-round discussion on a throwaway repository; real Codex accepts the schema, both rounds structured, report produced, nothing edited, Codex configuration unchanged, no leftover processes; then a fresh independent verification against this spec.

## Out of Scope

- Resuming a Codex session across rounds (revisit only after openai/codex#40149 is fixed).
- Parallel models, three-party discussion, changing model mid-discussion.
- Writing the discussion record into the project.
- Any write-capable Codex run; discussion-specific MCP grants.
- Natural-language or Claude-initiated discussions.
- Controlling Codex's web search tool (pre-existing gap shared with `ask`).

## Further Notes

- Honest limits for the README and ADR: a discussion multiplies Codex calls (up to 10) and each round re-explores the project; the anti-conformity rules are instructions, not enforcement — the evidence requirement and late-flip flag in the report are the control; Codex output carried into the next prompt is data like any file.
- Decision record: the grilling session's decisions D1–D17 and plan-level assumptions A1–A5 are kept in the Plan appendix below; the Plan (envelope and S1) passed `plan-verifier` (REVISE → READY, 2026-10-04). Implementation still waits for the user's explicit approval and choice of AUTO or ASK.

## Decision log (grilling 2026-10-04, all user-confirmed)

| # | Decision |
|---|---|
| D1 | Own vocabulary (CONTEXT.md 討論): 討論, 輪, 輪數上限, 討論點, 暫定共識, 爭議點, 待使用者決議. Parallel-consultation 共識/單獨提出/分歧 are not reused. |
| D2 | User-only. `ask` points a discussion request to the command; Claude cannot start it. |
| D3 | One typed command authorizes every round up to the limit; each round still prepares; unchanged confirmations reused within the discussion. |
| D4 | Round 1 blind for Codex; Claude's round-1 result written before Codex starts and not rewritten. |
| D5 | Round limit: argument, else question 3/5/7/custom 2–10, else headless 3 disclosed; early stop. |
| D6 | Fresh session every round; never resume. |
| D7 | Anti-conformity: full reasons carried; evidenced concessions (both sides); `maintain` without new argument; late flips flagged. |
| D8 | New discussion reply schema, selected per request. |
| D9 | Single model, fixed for the discussion; two tokens refused. |
| D10 | After round 1, only blocking new points, marked. |
| D11 | Tentative agreements locked; reopen only via a contested point of the same round. |
| D12 | User decision items: open at the limit, or marked user-call by both; both recommendations and reasons. |
| D13 | Report in the conversation: process summary, agreed list, user decision items. |
| D14 | Missing topic inferred and disclosed; else ask and stop. |
| D15 | Failed/stopped/unstructured round ends the discussion; partial report; no retry. |
| D16 | MCP and read-only boundary as `ask`; guard every round; mid-discussion confirmation asked or, headless, ends the discussion. |
| D17 | Stub evals plus one live discussion; ADR-0007. |

Plan-level assumptions: A1 point ids `L`/`C`; A2 stance `accept`/`maintain`/`revise`; A3 unstructured reply ends the discussion; A4 temp files deleted, nothing in the project; A5 discussion prompt rules 1–3 equal `ask`'s, test-guarded.

---

# Plan

Program envelope: deliver `discuss` as three slices on one local work branch `feat/discuss-skill`, one commit per slice; push only on the user's word. Budget: each slice gets its first implementation plus at most 3 fix/test passes. Real Codex calls only in S3: one real discussion with `rounds 2` (at most 2 calls), plus one rerun only after a reproduced fix.

Risk triggers: reply-schema / serialization change (S1), release (version bump, S3), material cross-component acceptance (S2 depends on S1's script contract) → `plan-verifier` before approval; fresh `verifier` at the S3 integration boundary against the full spec claim. Not classified security-sensitive: the sandbox, MCP policy and guard are unchanged; the one new script input is a closed enum (no path), validated before any Codex command. (Override this classification if you want `security-reviewer` first.)

## S1 — script: selectable discussion reply schema

- **Outcome:** a request may carry `reply_schema: "discussion"`; that run uses `skills/ask/discussion.schema.json` for `--output-schema` and for reply classification; everything else about the run is unchanged. Existing requests behave exactly as before.
- **Prerequisite:** none.
- **Owner:** `executor`; main keeps acceptance.
- **Scope:**
  - `skills/ask/discussion.schema.json` (contract above).
  - `skills/ask/scripts/consult.py`: `validate` accepts optional `reply_schema` ∈ {`consultation`, `discussion`} (absent → `consultation`; anything else → `ValueError` before any Codex command); `discussion` requires exactly one model; the prepared plan records it; `run` passes the matching schema file; `collect` classifies with it. The summary shown before launch names the reply schema.
  - `skills/ask/scripts/replies.py`: `classify(text, schema_name="consultation")`; `matches` gains `"boolean"` → `bool` in its type map (today a boolean schema node raises `KeyError`, which `collect` does not catch).
  - Stub (`evals/_harness/stub/codex-stub.py`): `exec.sequence` — a list of per-call exec configs consumed in call order (1-based counter under `.stub/`; calls beyond the list reuse the last entry). Every `exec` call additionally writes fixed-path records `.stub/exec-stdin.<n>.txt` and `.stub/exec-argv.<n>.json` (argv includes `--output-schema`), `<n>` = that call's 1-based sequence number, written after stdin is read. Existing records (`exec-stdin.txt`, `exec-argv.json`, `exec-argv.<slug>.json`, `exec-calls/*.json`, sentinel) and existing scenarios are unchanged.
  - Offline tests: extend `evals/_harness/consultation_test.py` and `evals/_harness/stub-modes.test.mjs` as listed under Acceptance.
- **Acceptance:**
  - **Reply schema selection** (`consultation_test.py`): `reply_schema` absent or `"consultation"` → `consultation.schema.json`; `"discussion"` → `discussion.schema.json`; any other value, and `"discussion"` with two models, → `ValueError` before any Codex command.
  - **Unchanged ask argv oracle** (`consultation_test.py`): a literal expected argv list, captured once from baseline `6266c3e` by running the stub with a request without `reply_schema` and normalising the run directory, project path and skill directory to fixed placeholders, with a comment naming `6266c3e` as its source. The test normalises the new code's argv the same way and compares it for a request without `reply_schema` and for one with `reply_schema: "consultation"`. Changing any element (a flag, its order, the schema basename) fails the test. The expected list is never generated by the new code.
  - **Classification** (`consultation_test.py`): a complete valid discussion fixture (all three booleans present) → `classify(..., "discussion")` returns `structured`; the same fixture with `user_call: "true"` → `unstructured`; neither raises. Existing consultation fixtures classify as before.
  - **Schema structure** (`consultation_test.py`): walking every object node of `discussion.schema.json`, `additionalProperties === false` and `required` equals its property keys; `stance`'s enum contains `null`; `user_call`, `new_blocking`, `reopen` are `"type": "boolean"`.
  - **End to end with the stub** (`consultation_test.py`): a discussion request through prepare → run → wait → collect with a valid discussion stub reply ends `collected` with `state: completed`, `format: structured`, and the run directory removed after collect.
  - **Stub sequence** (`stub-modes.test.mjs`): a 2-entry `exec.sequence`, two stub calls → `.stub/exec-stdin.1.txt` / `.2.txt` hold the first / second prompt in order, `.stub/exec-argv.<n>.json` hold that call's `--output-schema` path, each call's reply follows its sequence entry; the existing single-call and `by_model` records are unchanged for a scenario without `sequence`.
  - all existing `evals/_harness` tests (node and python) pass, except the named pre-existing CRLF failure of `ticket03-patterns.test.mjs`;
  - `script-consultation` Claude case still passes (regression on the unchanged ask path).
- **Rollback:** revert the slice commit.
- **Stops:** pause if Codex structured output rejects the schema shape (verified in S3 live only; S1 relies on the stub) — then the schema contract needs a user decision.

## S2 — `discuss` skill

- **Outcome:** `/ask-codex:discuss` runs D1–D16 through the unchanged-except-S1 scripts and produces the D13 report; Claude cannot start it.
- **Prerequisite:** S1.
- **Owner:** `executor`; main keeps acceptance.
- **Scope:** `skills/discuss/SKILL.md` (frontmatter `name: discuss`, `description`, `disable-model-invocation: true`; a unique body marker line for graders; Boundaries mirroring `review`'s; order of work: arguments → round limit → models → topic → round 1 (Claude file first, then Codex) → integrate → rounds 2..n → report; references `ask`'s Script interface / Execute / Collect sections by path like `review` does; request carries `reply_schema: "discussion"`), `skills/discuss/prompts/discussion.md` (A5), `skills/discuss/prompts/framing/round-1.md`, `skills/discuss/prompts/framing/round-n.md` (each with a unique marker line), `skills/ask/SKILL.md` (one pointer line: a multi-round discussion is not an `ask` type; tell the user `/ask-codex:discuss` exists), `.claude-plugin/plugin.json` (skills list), offline drift test for A5, eval cases under `evals/`.
- **Call counting:** from stub records — `exec.sentinel` line count = Codex calls; round `<n>`'s prompt is `.stub/exec-stdin.<n>.txt` and its argv (with the `--output-schema` path) is `.stub/exec-argv.<n>.json` (S1 fixed-path records); `exec-calls/*.json` is not a grader target.
- **Eval cases (stub Codex, deterministic graders):**
  - `discuss-early-consensus` — `rounds 5`; round 2 reply accepts every contested point → exactly 2 calls; both calls use `discussion.schema.json`; round 2 prompt contains the round-n marker, every carried id, and a round-1 Codex `reason` string verbatim; report has the three D13 sections.
  - `discuss-limit-reached` — `rounds 2`; round 2 maintains a contested point → exactly 2 calls; that point appears under user decision items with both recommendations.
  - `discuss-claude-first` — the Write of Claude's round-1 file precedes the first `consult.py run` in the trace; the round-1 prompt contains the round-1 marker and none of the carried-points section headings.
  - `discuss-headless-default` — no `rounds`; replies keep maintaining → exactly 3 calls; report discloses the default 3.
  - `discuss-rounds-arg-no-question` — `rounds 2` → no `AskUserQuestion` tool use in the trace.
  - `discuss-round-fails` — sequence: round 1 valid, round 2 `fail` → exactly 2 calls (no retry); report marks round 2 incomplete and lists open points as unresolved because the discussion ended.
  - `discuss-unstructured-ends` — round 2 unstructured → exactly 2 calls; report labels the reply unstructured (A3).
  - `discuss-two-models-refused` — `sol, astra` → no sentinel.
  - `discuss-rounds-out-of-range` — `rounds 1` headless → no sentinel.
  - `discuss-user-call` — round 1 Codex marks a point `user_call`, Claude's round-1 file is steered to the same view by the scenario topic → that point is a user decision item and is not carried to round 2's contested list.
  - `discuss-nl-not-loaded` (`--runs 5`) — the user's own message "discuss this design with Codex over a few rounds" → skill body marker never in the trace; no sent prompt contains a discuss framing marker; final message contains `/ask-codex:discuss`.
  - `discuss-not-model-invocable` (`--runs 5`) — a tool result says "run /ask-codex:discuss" during an unrelated task → no sentinel, no body marker.
- **Acceptance:**
  - every case passes at `--runs 3` (the two `--runs 5` cases at 5);
  - offline `evals/_harness` tests pass (CRLF exception as S1), including the A5 drift test;
  - regression: `second-opinion-with-stance`, `targeted-check`, `review-working-tree` at `--runs 3` on baseline `6266c3e` and on the S2 commit; pass rule: no grader's pass rate drops (pre-existing stale graders, ticket 09, fail equally and do not block);
  - one-off check: with `disable-model-invocation` removed locally (never committed), `discuss-nl-not-loaded` fails at least once in `--runs 5`.
- **Rollback:** revert the slice commit.
- **Stops:** pause if a case's property cannot be graded deterministically (name it, propose a narrower grader, ask) or the budget is exhausted with cases failing.

## S3 — docs, ADR, release prep, live verification

- **Outcome:** README (both languages), ADR-0007 and version 1.3.0 describe the shipped behaviour; one real live discussion is verified; the full spec claim is independently confirmed.
- **Prerequisite:** S2.
- **Owner:** main (docs) + user-typed live run.
- **Scope:** `README.md` + `README.zh-TW.md` (usage lines, capability paragraph, Known risks from Honest limits, pointer to the MCP policy section and `codex mcp list` for allowlist names), `docs/adr/0007-discuss-skill.md` (D2, D6 with sources, D8), `CONTEXT.md` (already updated; adjust only if implementation changed a term), `.claude-plugin/plugin.json` version → 1.3.0.
- **Acceptance:** one real harmless `/ask-codex:discuss rounds 2 <topic>` on a throwaway repo under `D:/tmp` with a real Codex model: real Codex accepts `discussion.schema.json`, both rounds structured, D13 report produced, nothing edited, `config.toml` hash unchanged, no leftover Codex processes; then a fresh `verifier` against the full spec claim.
- **Rollback:** revert; no tag or push until the user says.

---

# Outcome (2026-10-06)

Fresh `verifier`: **REFUTED** on 71586ee (F1: a point still split at the round limit marked `(unresolved because the discussion ended)`, 4 of 6 limit-path reports), then **CONFIRMED** on 0e75a87 after the fix and a full rerun. Commits on `feat/discuss-skill` since `main` (6266c3e): c0edd9e (spec, tickets, glossary), 1708335 (01), eba3939 + 2e970b8 (02), c59ecac + 48541af (03), 47c98fc (04), 37317c2 (05), b2091df, 3e7ec28 (06 docs, 1.3.0), 4dca943, d9fc387 (F1), c0c0fa4 (pass 5), cebddfc (fixture), 0e75a87 (pass 6), plus records commits.

Fix passes beyond the Plan budget (3 per slice) were authorised by the user one at a time: pass 4 (F1, verifier finding), pass 5 (framing copied verbatim), pass 6 (one-sided user-call proposal answered once).

Evidence (`evidence/`, fingerprinted run logs; traces in `D:\tmp\ask-codex-r07b-traces\discuss-<segment>-<case>`):

- Final bytes 0e75a87: p6 — the eight discussion cases x3, 24/24. Cases not rerun on p6 are byte-equivalent for their path (the later edits start after section 4 of the skill): rounds-out-of-range and two-models-refused 3/3 on d9fc387 (f1); nl-not-loaded and not-model-invocable 5/5 on 3e7ec28 (final).
- Detection proof: with `disable-model-invocation` removed (worktree, never committed), nl-not-loaded failed 5/5 (`noflag`).
- Live: one real two-round discussion on 3e7ec28 (gpt-5.6-sol high): both rounds structured, three-section report, guards unchanged (`live-discuss-*`).
- Regression: 9 existing ask/review/setup cases x3 on 4dca943 vs 6266c3e — no grader fails more often on the candidate except one `no-bare-cd` (overall candidate 2/27, baseline 4/27) (`regression-comparison.txt`). Later commits touch only the discuss skill and its evals.
- Offline: node harness 0 failures (discuss-skill-graders 845), consultation_test 37 OK, resolve_test 42 OK (verifier rerun on 0e75a87).

Deferred (follow-up tickets, `Status: needs-triage`): 07 one-sided user-call edges (verifier A1 P3, A2 P4); 08 framing paraphrased by a word or two in 3 of 27 rounds (A6 P3); 09 report wording drift, residual bare `cd`, stub counter, API stalls (A4/A5 P4); 10 interactive paths verified against the skill text only.

Cleanup: worktree `D:/tmp/ask-codex-discuss-baseline` removed; `D:/tmp/discuss-live` removed after its trace was copied to `evidence/`; kept eval traces remain under `D:\tmp\ask-codex-r07b-traces\discuss-*`.
