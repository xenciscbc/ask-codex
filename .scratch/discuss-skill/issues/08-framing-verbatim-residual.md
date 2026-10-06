# 08 — Framings still paraphrased by a word or two in a few rounds

Status: needs-triage

**What to build:** the final verifier (A6, P3) compared every p6 round-n prompt with `round-n.md`: 24 of 27 were verbatim; 3 changed one or two words (`accept` → `agree`, an added "after a position was given"). The meaning and every rule still reached Codex; the `round-2-marker` grader checks only the first line, so it cannot see this. Before pass 5 (c0c0fa4) 2 of 56 round-2 prompts replaced the whole framing with a self-written line; that no longer occurs.

**Blocked by:** None — can start immediately.

- [ ] A grader compares the whole framing text in `.stub/exec-stdin.<n>.txt` with `round-1.md` / `round-n.md` (CRLF-normalised), proven offline on the three kept p6 traces (`discuss-p6-discuss-claude-first/claude-eval-jigiGg`, `discuss-p6-discuss-unstructured-ends/claude-eval-OLqofk`, `discuss-p6-discuss-user-call/claude-eval-8XS3wi`) — they must fail, a verbatim one must pass.
- [ ] Measure the rate over at least 10 runs; decide whether wording (for example a fill-by-copy instruction or a script-side framing insert) is worth a change.
