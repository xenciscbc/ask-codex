# 07 — One-sided user-call proposals: accept with a "right answer" reason, and the lapsed-proposal line

Status: resolved — see Comments (2026-10-06)

**What to build:** two edges of the pass-6 rule (0e75a87) that the stub cannot exercise, raised by the final verifier as A1 (P3) and A2 (P4).

- **A1 (P3):** a point Claude proposed as a user call becomes a user decision item when Codex returns `accept`, even with `user_call: false`. Real Codex may accept Claude's substantive statement while saying in its reason that the point has a right answer; the point then lands under "For you to decide" instead of Agreed. The round-n framing (`round-n.md`) tells Codex to set `user_call` only when it agrees it is a user call, so the skill rule and the framing disagree on what a plain `accept` means here. Decide which reading wins and align both texts.
- **A2 (P4):** the skill says a mark stands for the rest of the discussion and a one-side-marked block carries the `User call proposed by …` line, but also that a lapsed proposal is never asked again. Read literally, a lapsed proposal's line is still appended. No extra round results; make the text unambiguous.

**Blocked by:** None — can start immediately.

- [ ] Skill and `round-n.md` agree on what `accept` with `user_call: false` means for a point proposed as a user call.
- [ ] A lapsed proposal's line is not carried into later blocks.
- [ ] A stub fixture returns `accept` + `user_call: false` + a "has a right answer" reason for a Claude-proposed user call, and one returns `maintain` on such a point; graders check where each point lands and that no later block carries a lapsed proposal.

## Comments

- 2026-10-06 — d83ef1e (executor) + fix 2496be4. Design (user-approved): a "User call proposed by Claude" line must be answered with an explicit `user_call`; `true` completes the pair, `false` makes the proposal lapse whatever the stance and however thin the reason, and the stance then settles the substance (`accept` = agreement); an unanswered proposal gets one more round; a lapsed line is never carried into a later block. New cases `discuss-user-call-accept-false`, `discuss-user-call-lapse` (rounds 3).
- Evidence: fu (292e357) — one lapse run re-asked on a thin reason → 2496be4; fu2 (2496be4) — lapse 3/3, accept-false 2/3, user-call 2/3 (one bare cd); a2 (eedf688) — early-consensus 3/3, every run carried a Claude proposal in round 2, got a generic `accept` + `user_call: false`, and stopped without re-asking (the variant the fresh verifier flagged as unverified).
- Fresh verifier: CONFIRMED on eedf688. Deferred to ticket 11: verifier A1 (P3) — one accept-false run still listed a lapsed proposal whose statement was "the owner decides" as a user decision item (the verifier judged Codex's answer consistent, not self-contradictory, so this is a residual of the new rule, not a fixture artifact); A3 (P4) dead "proposed by Codex" block wording; A4 (P4) the new cases do not grade where a lapsed point lands.
