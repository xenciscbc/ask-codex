# 03 — The user chooses the round limit when starting a discussion

**What to build:** when the command has no `rounds <n>`, Claude asks for the round limit with an interactive question offering 3, 5, 7 or a custom number; a custom number outside 2–10 is refused and asked again. Without an interactive question tool (headless), the discussion uses 3 rounds and the report says the default was used without asking. An out-of-range `rounds <n>` in the arguments is refused (asked again interactively; headless stops before any Codex call). Part of Plan slice S2 (spec user stories 6–9).

**Blocked by:** 02 — `/ask-codex:discuss rounds <n> <topic>` runs a discussion end to end.

**Status:** resolved — see Comments (2026-10-06)

- [ ] No `rounds` in the command, interactive → one question with options 3 / 5 / 7 / custom; the answer sets the limit.
- [ ] Custom answer outside 2–10 → refused and asked again.
- [ ] Eval `discuss-headless-default` (no `rounds`, replies keep maintaining): exactly 3 Codex calls; the report discloses the unasked default of 3.
- [ ] Eval `discuss-rounds-out-of-range` (`rounds 1`, headless): no Codex call; the report states the allowed range.
- [ ] 02's evals still pass at their stated runs.

## Comments

- 2026-10-06 — Implemented in c59ecac (executor), grader fix 48541af (`default-disclosed` tolerates a clause inside the parentheses). Final bytes 0e75a87: `discuss-headless-default` 3/3 (p6), `discuss-rounds-out-of-range` 3/3 (f1), `discuss-rounds-arg-no-question` 3/3 (p6). Two earlier timeouts were single API stalls (one 1165 s gap before a response), not skill behaviour. The interactive question (3/5/7/custom) is checked against the skill text only; no interactive eval exists (follow-up ticket 10).
