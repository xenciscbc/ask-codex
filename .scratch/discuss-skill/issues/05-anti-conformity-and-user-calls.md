# 05 — Concessions need evidence; user-preference points go to the user

**What to build:** the discussion resists false convergence and stops debating what only the user can decide. Each side's concession must cite specific evidence (file location, document, counter-example); a concession without it is reported as an unevidenced concession. Codex is told to answer `maintain` when it has no new substantive argument. Points that flip in round 3 or later are flagged in the report. After round 1 a new point is accepted only when it would change the conclusion and is marked as such. A tentative agreement can be reopened only by naming the contested point of that round whose conclusion affects it. Either side can mark a point as a preference/authority question; once both have, it stops being debated and becomes a user decision item with both sides' recommendation and reason. The same rules apply to Claude's side. Part of Plan slice S2 (spec user stories 25–31, 34).

**Blocked by:** 02 — `/ask-codex:discuss rounds <n> <topic>` runs a discussion end to end.

**Status:** ready-for-agent

- [ ] The round-n framing states the evidence rule for concessions, the `maintain` rule, blocking-only new points, the reopen rule and user-call marking; the report rules state the unevidenced-concession label and the late-flip flag for both sides.
- [ ] Eval `discuss-user-call` (round 1: Codex marks a point user-call and the scenario steers Claude to the same view): that point is a user decision item with both recommendations and is absent from round 2's contested points in the round-2 prompt.
- [ ] Round 2's prompt lists tentative agreements as locked background, separate from contested points (graded on the per-round prompt record).
- [ ] 02's evals still pass at their stated runs.
