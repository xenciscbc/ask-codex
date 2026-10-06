# 05 — Concessions need evidence; user-preference points go to the user

**What to build:** the discussion resists false convergence and stops debating what only the user can decide. Each side's concession must cite specific evidence (file location, document, counter-example); a concession without it is reported as an unevidenced concession. Codex is told to answer `maintain` when it has no new substantive argument. Points that flip in round 3 or later are flagged in the report. After round 1 a new point is accepted only when it would change the conclusion and is marked as such. A tentative agreement can be reopened only by naming the contested point of that round whose conclusion affects it. Either side can mark a point as a preference/authority question; once both have, it stops being debated and becomes a user decision item with both sides' recommendation and reason. The same rules apply to Claude's side. Part of Plan slice S2 (spec user stories 25–31, 34).

**Blocked by:** 02 — `/ask-codex:discuss rounds <n> <topic>` runs a discussion end to end.

**Status:** resolved — see Comments (2026-10-06)

- [ ] The round-n framing states the evidence rule for concessions, the `maintain` rule, blocking-only new points, the reopen rule and user-call marking; the report rules state the unevidenced-concession label and the late-flip flag for both sides.
- [ ] Eval `discuss-user-call` (round 1: Codex marks a point user-call and the scenario steers Claude to the same view): that point is a user decision item with both recommendations and is absent from round 2's contested points in the round-2 prompt.
- [ ] Round 2's prompt lists tentative agreements as locked background, separate from contested points (graded on the per-round prompt record).
- [ ] 02's evals still pass at their stated runs.

## Comments

- 2026-10-06 — Implemented in 37317c2 (executor, worktree). Later fixes: b2091df (user decision items collected from the ledger in a fixed order; every id stays visible; opposed pairs `<C id> vs <L id>`), c0c0fa4 (framings copied verbatim), 0e75a87 (user-authorised pass 6: a one-sided user-call proposal is answered once — Codex's accept or user_call completes the pair, maintain/revise makes it lapse). Final bytes: `discuss-user-call` 3/3 (p6). Residual advisories A1/A2/A6 from the final verifier are follow-up tickets 07 and 08.
