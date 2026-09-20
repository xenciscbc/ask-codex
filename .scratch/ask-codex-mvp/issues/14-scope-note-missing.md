# 14 — The reply often omits how long a model choice applies

**What to build:** when the user names a model or effort that differs from what would otherwise be used and there is no `AskUserQuestion` to ask with, the reply says that the choice applies to this consultation only — every time, not sometimes.

**Blocked by:** None — can start immediately.

**Status:** resolved (reliability ticket 05, 2026-09-20)

## Evidence (resampling at `f5cfb07`, 2026-09-16)

`alias-astra` with `--runs 3`: **1 of 3 runs passed.** Runs 1 and 3 failed the `scope-note` judge 3-0; run 2 passed. The case is `/ask-codex:ask astra …` in a session whose default model is different and where `AskUserQuestion` is unavailable, so step 0 item 7 requires "apply it to this consultation only and say so in the result".

The behaviour exists — the live A1 and I2 runs did state it — but it is roughly a coin flip in the eval sandbox.

## Impact

The user can reasonably conclude the model choice persists for the session when it does not, and will be surprised when the next consultation uses a different model.

## Acceptance criteria

- [x] `alias-astra` passes `scope-note` on 3 of 3 runs.
- [x] The skill's step 0 item 7 makes the note a fixed line rather than a description, so a deterministic grader can check it (the llm judge alone has proven lenient elsewhere).
- [x] The paired case where the choice *equals* the setting in force still says nothing (no spurious note).

## Comments

**2026-09-20 — resolved by reliability ticket 05.** Round 5 on the final bytes (2026-09-20, sonnet, WSL): `alias-astra` 5/5 at 1.00 — `scope-line` (new regex: fixed words, full slug `gpt-6-astra`, `effort medium`) 5/5 and `scope-note` (llm) 5/5; control `override-restated-no-prompt` — `no-scope-line` (new, not_contains) 5/5 and `no-scope-prompt` (llm) 5/5. Offline: `evals/_harness/ticket-r05-graders.test.mjs` 14/14 (the exact line passes plain, bold and backticked; an alias-only slug, a missing effort, a paraphrased sentence and a translation fail).

How it got there, because the first wording was not enough: a fixed line in step 10 alone gave 3/5 (the line was simply forgotten) and the control wrote the line 1 time in 3; writing the line "now" in step 0 fixed the positive case (5/5 from round 2 on) but the control stayed at 1 failure in 3–5 through three wordings. The kept trace of a failing control run (`.scratch/ask-codex-reliability/evidence/05-traces/`) shows the first message going straight to "AskUserQuestion isn't available, so this consultation only" — the comparison with the session setting was skipped, not got wrong. What fixed it is making the comparison a visible step: step 0 item 7 is now an ordered decision whose second step is a working line, `Model baseline: … ; named: … — <same|different>.`, and the branch follows from that word. The working line belongs to the run; step 10 does not repeat it.

Eval spend for this ticket: five rounds, about USD 20.1 (3.85 + 4.01 + 4.85 + 2.45 + 4.96). No Codex call.
