# 07 — One-sided user-call proposals: accept with a "right answer" reason, and the lapsed-proposal line

Status: needs-triage

**What to build:** two edges of the pass-6 rule (0e75a87) that the stub cannot exercise, raised by the final verifier as A1 (P3) and A2 (P4).

- **A1 (P3):** a point Claude proposed as a user call becomes a user decision item when Codex returns `accept`, even with `user_call: false`. Real Codex may accept Claude's substantive statement while saying in its reason that the point has a right answer; the point then lands under "For you to decide" instead of Agreed. The round-n framing (`round-n.md`) tells Codex to set `user_call` only when it agrees it is a user call, so the skill rule and the framing disagree on what a plain `accept` means here. Decide which reading wins and align both texts.
- **A2 (P4):** the skill says a mark stands for the rest of the discussion and a one-side-marked block carries the `User call proposed by …` line, but also that a lapsed proposal is never asked again. Read literally, a lapsed proposal's line is still appended. No extra round results; make the text unambiguous.

**Blocked by:** None — can start immediately.

- [ ] Skill and `round-n.md` agree on what `accept` with `user_call: false` means for a point proposed as a user call.
- [ ] A lapsed proposal's line is not carried into later blocks.
- [ ] A stub fixture returns `accept` + `user_call: false` + a "has a right answer" reason for a Claude-proposed user call, and one returns `maintain` on such a point; graders check where each point lands and that no later block carries a lapsed proposal.
