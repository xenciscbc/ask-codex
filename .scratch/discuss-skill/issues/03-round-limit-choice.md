# 03 — The user chooses the round limit when starting a discussion

**What to build:** when the command has no `rounds <n>`, Claude asks for the round limit with an interactive question offering 3, 5, 7 or a custom number; a custom number outside 2–10 is refused and asked again. Without an interactive question tool (headless), the discussion uses 3 rounds and the report says the default was used without asking. An out-of-range `rounds <n>` in the arguments is refused (asked again interactively; headless stops before any Codex call). Part of Plan slice S2 (spec user stories 6–9).

**Blocked by:** 02 — `/ask-codex:discuss rounds <n> <topic>` runs a discussion end to end.

**Status:** ready-for-agent

- [ ] No `rounds` in the command, interactive → one question with options 3 / 5 / 7 / custom; the answer sets the limit.
- [ ] Custom answer outside 2–10 → refused and asked again.
- [ ] Eval `discuss-headless-default` (no `rounds`, replies keep maintaining): exactly 3 Codex calls; the report discloses the unasked default of 3.
- [ ] Eval `discuss-rounds-out-of-range` (`rounds 1`, headless): no Codex call; the report states the allowed range.
- [ ] 02's evals still pass at their stated runs.
