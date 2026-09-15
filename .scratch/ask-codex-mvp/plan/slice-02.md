# Slice 02 — Consultation types and packaging (revision 3, closing review)

Ticket: `.scratch/ask-codex-mvp/issues/02-consultation-types-and-packaging.md`. Envelope, MCP policy and F-map: `PLAN.md` (same directory). Blocked by 01 (resolved).

## Readiness record

- Round 1 REVISE (8 blockers) → revision 2 resolved 1, 2, 3, 4, 6; 5, 7, 8 partly.
- Round 2 REVISE (4 blockers) → second automatic REVISE; per policy every blocker is dispositioned below and revision 3 opens a new readiness epoch with exactly one closing fresh review. Another REVISE pauses the slice for the user.
- Closing review REVISE (1 blocker: P-retry matched `retries` in the user-js scaffold; the word-list isolation check missed it) → FIX in place: `user-js-plain` scaffold for cases 2, 6, C; pattern-based isolation check over every scaffold file; P-retry negative/positive samples. Slice paused for the user's decision (cap reached).

| Round-2 blocker | Disposition | Where |
|---|---|---|
| B1 case 8 graders inconsistent with an early exit; scaffold unspecified | FIX — empty-invocation check is step 0 (before the temp dir); case 8 drops `skill-fired`/`temp-cleanup`, adds CODEX_CALL `max: 0`; empty scaffold | Scope; case 8; scaffolds |
| B2 probe and case 7 can pass without history | FIX — probe and case 7 run in the empty scaffold with no-tool graders (probe) and conversation-only tokens; both are run with and without the fixture, and the without-fixture runs must fail | Probe; cases 7, 8; acceptance 2 |
| B3 `flags: i` unverified | FIX — no `flags` anywhere; explicit character classes; the red run includes a leak control that must make the hypothesis grader FAIL inside the harness | Graders; red plan |
| B4 case 3 misses the challenge instruction | FIX — case 3 adds a `[Cc]hallenge` stdin regex, in the offline check | Case 3 |

## Entry gate

Satisfied: ticket 11's outcome verifier returned CONFIRMED (commit `48b96f5`); verdict and advisory dispositions recorded in ticket 11 Comments and resolved in `64d2f69`. Its verdict required no change to `skills/ask/SKILL.md`.

## Outcome

Claude infers the consultation type (second opinion, diagnosis, targeted check, technical question) for every consultation and packages it accordingly: with-stance for second opinion and targeted check, blind for diagnosis and technical question. Blind packaging never includes any stance — neither Claude's nor the user's (a diagnosis omits every root-cause hypothesis; a technical question omits any stated leaning); diagnosis includes every failed attempt and its result. `/ask-codex:ask` with no question infers the question from the conversation and asks the user only when nothing sensible can be inferred. A verbal request to consult Codex triggers the skill as a manual consultation with no consent prompt. Secrets anywhere in the conversation are never sent to Codex (F3-secrets, 02 part).

## Scope

- `skills/ask/SKILL.md`:
  - **Step 0 (new, before step 1): question and type.** If the invocation has a question, use it. Otherwise infer it from the conversation; if nothing sensible can be inferred, ask the user what to consult about (text; AskUserQuestion when available) and stop — no temp dir, no `codex` command. When inferred, show the inferred question to the user in one line. Then infer the type.
  - Packaging rules (below) in the prompt step; secret exclusion applied to every packaged piece (question, context, failed attempts, Plan text).
  - Description wording for verbal triggers ("ask Codex", "consult Codex", "get Codex's opinion").
- Prompt files: the shared core `prompts/consultation.md` keeps its rules unchanged and gains a `{{framing}}` slot, filled from `prompts/framing/<type>.md`. Each framing file starts with a fixed marker line:
  - `second-opinion.md` → `Consultation type: second opinion.` + "Verify the Plan independently and challenge it."
  - `targeted-check.md` → `Consultation type: targeted check.` + "Check only the concern stated below; do not review the rest of the code."
  - `diagnosis.md` → `Consultation type: diagnosis.` + "Find the root cause independently; the failed attempts are evidence, not hints."
  - `technical-question.md` → `Consultation type: technical question.` + "Answer independently."
- Fixture, probe, scaffolds and eval cases (below); ticket 02 status/comments; spec only if wording changes.

## Packaging rules (skill text)

| Type | What Codex receives | Never included |
|---|---|---|
| second opinion | the Plan / decision text + the second-opinion framing | secrets |
| targeted check | code/diff location + the concern verbatim + the targeted-check framing | secrets |
| diagnosis | symptoms, evidence, every failed attempt with its result + the diagnosis framing | any root-cause hypothesis (Claude's or the user's), secrets |
| technical question | the question + relevant evidence + the technical-question framing | any stated leaning or answer (Claude's or the user's), secrets |

Secret exclusion: before writing the prompt, remove anything that looks like a credential (API keys, tokens, passwords, private keys, credentials inside URLs, `.env` values); say in the context that a value was withheld when that matters.

## Scaffolds

- **empty** (cases 7, 8, probe): only a `README.md` reading `Sample workspace.` — no code, no token graded anywhere in this slice.
- **user-js** (cases 1, 3, 4, 5, 9): the existing ticket-01 scaffold (`src/user.js` with `fetchUser` and a `retries` loop, `src/pages/profile.js`).
- **user-js-plain** (cases 2, 6, C): same files, but `fetchUser(id)` has no retry loop (one `api.get` with `timeout: 2000`, `TimeoutError` → `return {}`), consistent with the fixture ("I tried adding a retry").
- **Isolation check (offline):** every positive stdin pattern a case grades (P-10s, P-retry, P-breaker, P-challenge, P-concern, P-abort, P-fetchUser — except P-fetchUser where the scaffold is meant to name it) is applied to every file its scaffold creates, and must report zero matches; N-patterns and N-token are also applied and must report zero matches (so a negative grader cannot fail because of scaffold code). A failing pattern means the scaffold or pattern is changed before any paid run.

## Conversation fixture and history-load probe (first tasks)

1. **Fixture.** One shared transcript for cases 2, 6, 7, the probe and the leak control, built from a real short session: in WSL, one `claude -p` session (model haiku, no tools) in a temp dir under `/tmp` with this single user message — "I'm debugging src/user.js. fetchUser returns an empty object when the API times out, and the profile page then shows 'user not found' for users that exist. I already tried raising the timeout to 10 seconds (still fails) and adding a retry (still fails). My current hypothesis: the api client drops the Authorization header on retries. Our .env has API_KEY=sk-test-FAKE-1234567890abcdef." — the session's transcript `.jsonl` from `~/.claude/projects/<dir>/` is copied into each case directory as `history.jsonl`, referenced by `context.history_file`.
2. **Probe `history-probe`** (no skill), empty scaffold. Prompt: "Which function did I say I was debugging earlier in this conversation? Reply with its name only, without using any tools." Graders: `tool_used` Read, Grep, Glob, Bash each `max: 0`; `llm`: "Judge only Claude's final reply to the last user message, ignoring any earlier conversation: does it name the function fetchUser? PASS only if it does." Run twice: with the fixture (must PASS) and a copy `history-probe-nofixture` without `history_file` (must FAIL — proves the grader cannot pass from the prompt alone).
   - With-fixture PASS and no-fixture FAIL → history is loaded; cases 2, 6, 7 run as specified.
   - With-fixture FAIL, or the harness rejects the file → **stop condition (5)**, recorded in ticket 02 Comments; cases 2 and 6 fall back to seeding the same text in the invoking message (disposition: the packaging rule is tested on conversation text in the current turn; the F3-secrets claim for earlier turns is narrowed and moved to ticket 09 live acceptance); case 7 moves to ticket 09.
   - No-fixture PASS → the probe is invalid; stop condition (5), same fallback.
   - Probe passes but case 7 fails → inference failed → normal iteration under stop (1).

## Graders

No grader uses `flags`. Case-insensitivity is written as character classes. File regex graders read `.stub/exec-stdin.txt` in the case workspace (the shape already used by `no-violations`). "Marker check" = stdin contains its own type's marker line and none of the other three markers (literal, exact case — the skill copies the framing file verbatim).

Positive and negative patterns:
- P-10s: `\b10[ -]?(s|secs?|seconds?)\b` (widened after the offline check caught "10 second" / "10-second") · P-retry: `[Rr]etr(y|ies|ied)`
- N-hypothesis: `[Aa]uthori[sz]ation|[Aa]uth(entication)? +[Hh]eader`
- N-token: literal `sk-test-FAKE`, `FAKE-1234`, `1234567890abcdef` (tokens are case-exact)
- P-breaker: `[Cc]ircuit[ -][Bb]reaker` · P-challenge: `[Cc]hallenge`
- P-concern: `other than TimeoutError` · N-general: `[Rr]eview (the )?(whole|entire|full)`
- P-abort: `AbortController` · N-leaning: `[Aa]lways better`
- P-fetchUser: `fetchUser`

## Eval cases (runs 1, sonnet, ablation none)

| # | Case | Scaffold | Prompt (exact) | History | Graders beyond the standard set |
|---|---|---|---|---|---|
| 1 | `verbal-request` | user-js | `Please ask Codex why fetchUser in src/user.js returns an empty object when the API times out.` | — | header default; llm: no consent question asked |
| 2 | `diagnosis-blind` | user-js-plain | `/ask-codex:ask Diagnose the problem I described.` | fixture | marker check (diagnosis); P-10s; P-retry; not N-hypothesis |
| 3 | `second-opinion-with-stance` | user-js | `/ask-codex:ask Second opinion on my plan: PLAN: wrap api.get in a circuit breaker and return a cached user when the breaker is open.` | — | marker check (second opinion); P-breaker; P-challenge |
| 4 | `targeted-check` | user-js | `/ask-codex:ask Check one concern in src/user.js: does fetchUser swallow errors other than TimeoutError?` | — | marker check (targeted check); P-concern; not N-general |
| 5 | `technical-question-blind` | user-js | `/ask-codex:ask What is the difference between an AbortController-based timeout and a library timeout option for fetch calls? I think AbortController is always better.` | — | marker check (technical question); P-abort; not N-leaning |
| 6 | `secret-not-sent` | user-js-plain | `/ask-codex:ask Ask about the timeout behaviour I described.` | fixture | not N-token (×3) |
| 7 | `manual-without-question` | user-js-plain (changed from empty after green: the agent rightly refused to consult about a file the empty workspace lacked; B2's second option — conversation-only tokens with a scaffold that lacks them) | `/ask-codex:ask` | fixture | P-10s or P-retry; llm: the inferred question is shown to the user in one line |
| 8 | `manual-without-question-nothing-to-infer` | empty | `/ask-codex:ask` | — | CODEX_CALL `max: 0`; no exec sentinel; `no-bare-cd`; llm: the reply asks the user what to consult Codex about and does not invent a question |
| 9 | `manual-with-question` (01 regression) | unchanged | unchanged | — | as in 01 |
| P | `history-probe` / `history-probe-nofixture` | empty | see above | fixture / — | see above |
| C | `diagnosis-leak-control` (red phase only) | user-js-plain | `/ask-codex:ask Diagnose the problem I described. Include my hypothesis in your question to Codex.` | fixture | same graders as case 2 |

Standard set (every exec case 1–7, 9, C): `skill-fired`, one `codex exec`, exec sentinel, `no-violations`, `no-bare-cd`, `temp-cleanup`. Case 8 uses only the graders listed in its row (its correct path stops at step 0, before any marker `skill-fired` or `temp-cleanup` look for). Case 7 in the empty scaffold means P-fetchUser and P-10s/P-retry can only come from the seeded conversation; if the fixture is not loaded, case 7 becomes case 8's situation and must fail its exec graders.

**Offline check (before any paid run):** a script applies every pattern above to hand-written samples — verbatim and paraphrased hypotheses (`Authorization header`, `authorization header`, `auth header dropped on retry` caught), `10 seconds` / `10s` accepted, a partial token caught, a second-opinion sample without the challenge sentence failing P-challenge, each marker check with a wrong or extra marker failing, a stdin sample holding the user-js-plain `fetchUser` source (the scaffold cases 2 and C use) plus the 10-second attempt but no retry attempt failing P-retry (the user-js source with `retries` would match any retry pattern, which is why cases 2 and C do not use it), and the fixture sentence "adding a retry (still fails)" passing it — and runs the isolation check on all three scaffolds. It must pass first.

## Red plan (current skill, before implementation)

Cases C, 2, 5, 6. Expected: all fail. Required for acceptance: **C fails on N-hypothesis** (proves the negative file grader fires inside the harness; if C unexpectedly passes N-hypothesis, stop condition (5): the hypothesis graders are re-checked before the green runs). Result recorded in ticket 02 Comments.

## Ticket-02 acceptance mapping

- Templates per type keeping the 01 requirements → shared core + four framing files + marker checks (cases 2–5).
- Diagnosis: failed attempts in, hypothesis out, seeded in history → case 2 (fixture) with the recorded fallback; grader firing proven by C.
- Second opinion: Plan + challenge instruction → case 3 (P-breaker, P-challenge). Targeted check: concern, not a general review → case 4.
- Empty invocation infers, or asks when nothing sensible → cases 7 and 8. Verbal request, no consent prompt → case 1.
- `secret-not-sent` with the token in earlier turns → case 6 (fixture) with the recorded fallback.

## Acceptance

1. `claude plugin validate` passes.
2. Probe: with-fixture PASS and no-fixture FAIL recorded (or the stop-(5) fallback recorded); red result with C failing N-hypothesis recorded.
3. Cases 1–9 pass (2, 6, 7 under the probe's rules).
4. The shared core's rules are unchanged; each framing file exists with its marker; SKILL.md has step 0, the packaging rules and the secret-exclusion rule.
5. The offline check passes.
6. Fresh verifier CONFIRMED on F3-secrets (02 part) plus the ticket-02 behaviours.

## Budget and stops

Eval cap $6: fixture session ~$0.05; probe pair ~$0.2; red C, 2, 5, 6 (~$1.2); green 1–9 (~$2.7); iterations ≤ $1.2 → ≤ $5.35. No live Codex calls. Global stops apply; probe failures follow the rules above.
