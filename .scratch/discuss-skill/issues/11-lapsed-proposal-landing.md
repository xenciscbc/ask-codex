# 11 — Where a lapsed user-call proposal lands, and two wording leftovers

Status: needs-triage

**What to build:** the fresh verifier of tickets 07–09 (2026-10-06, CONFIRMED on eedf688) left three deferred advisories.

- **A1 (P3):** one `discuss-user-call-accept-false` run (`D:\tmp\ask-codex-r07b-traces\discuss-fu2-discuss-user-call-accept-false\claude-eval-qoICub.jsonl`) listed L5 twice — under Agreed and, with `(your preference or authority)` and `Codex recommends: none returned`, under For you to decide — after Codex returned `accept` + `user_call: false` on L5, whose statement was itself "what a locked-out user sees is the product owner's decision". The verifier judged that answer consistent (who decides is settled by `docs/decisions.md`), so the run broke the rule that a lapsed proposal never becomes a user decision item. The report explained itself; impact low. Also make the fixture realistic: answer only the ids Claude issued instead of L1–L30 with one identical reason.
- **A3 (P4):** `SKILL.md` (block lines) and `discussion.md` rule 4 still mention a `User call proposed by Codex:` block line that can never occur, because Claude answers a Codex proposal at once.
- **A4 (P4):** the new cases only grade that no `(your preference or authority)` item appears; nothing grades that the lapsed point lands under Agreed (accept) or stays split (maintain), so a report that dropped it would pass.

**Blocked by:** None — can start immediately.

- [ ] Rule or wording that keeps a lapsed proposal out of "For you to decide" even when its statement is about ownership, measured over at least 5 runs.
- [ ] Dead `proposed by Codex` block wording removed or made consistent.
- [ ] Graders that the lapsed point is listed under Agreed (accept-false) or still split (lapse), proven offline.
