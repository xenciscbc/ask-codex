# 14 — The reply often omits how long a model choice applies

**What to build:** when the user names a model or effort that differs from what would otherwise be used and there is no `AskUserQuestion` to ask with, the reply says that the choice applies to this consultation only — every time, not sometimes.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Evidence (resampling at `f5cfb07`, 2026-09-16)

`alias-astra` with `--runs 3`: **1 of 3 runs passed.** Runs 1 and 3 failed the `scope-note` judge 3-0; run 2 passed. The case is `/ask-codex:ask astra …` in a session whose default model is different and where `AskUserQuestion` is unavailable, so step 0 item 7 requires "apply it to this consultation only and say so in the result".

The behaviour exists — the live A1 and I2 runs did state it — but it is roughly a coin flip in the eval sandbox.

## Impact

The user can reasonably conclude the model choice persists for the session when it does not, and will be surprised when the next consultation uses a different model.

## Acceptance criteria

- [ ] `alias-astra` passes `scope-note` on 3 of 3 runs.
- [ ] The skill's step 0 item 7 makes the note a fixed line rather than a description, so a deterministic grader can check it (the llm judge alone has proven lenient elsewhere).
- [ ] The paired case where the choice *equals* the setting in force still says nothing (no spurious note).
