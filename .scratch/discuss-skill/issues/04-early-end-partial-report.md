# 04 — A round that cannot complete ends the discussion with a partial report

**What to build:** when a round fails, is stopped, ends with an unconfirmed stop, returns an unstructured reply, or (headless) needs a new MCP confirmation, the discussion ends without retrying. The user gets a partial report built from the last completed round: which round did not complete and why, the agreed list so far, and every still-open contested point listed as "unresolved because the discussion ended" — distinct from points that stayed split after debate. An unstructured reply is quoted or summarised under an explicit unstructured label and never parsed into stances. Interactively, a new confirmation mid-discussion is asked and the round continues after the answer. Part of Plan slice S2 (spec user stories 42, 44–46).

**Blocked by:** 02 — `/ask-codex:discuss rounds <n> <topic>` runs a discussion end to end.

**Status:** resolved — see Comments (2026-10-06)

- [ ] Eval `discuss-round-fails` (round 1 valid, round 2 fails): exactly 2 Codex calls (no retry); report marks round 2 incomplete with its reason and lists open points as unresolved because the discussion ended.
- [ ] Eval `discuss-unstructured-ends` (round 2 unstructured): exactly 2 calls; report labels the reply unstructured and invents no stances.
- [ ] A stop or unconfirmed stop follows `ask`'s stop and report rules, then ends the discussion with the partial report (no further round prepared).
- [ ] Headless pending confirmation mid-discussion → no further Codex call; pending items and their decline outcomes in the partial report.
- [ ] 02's evals still pass at their stated runs.

## Comments

- 2026-10-06 — Implemented in 47c98fc (executor, worktree). Later fixes on the same path: 4dca943 (exact partial-report shape after an unstructured quote landed inside the `Round 2:` line and opposed pairs lost the marker) and d9fc387 (verifier F1: three markers chosen by why an item is listed; `(still split at the round limit)` for a discussion that ran its course). Final bytes 0e75a87: `discuss-round-fails` 3/3, `discuss-unstructured-ends` 3/3 (p6). Stop, unconfirmed stop and a headless mid-discussion confirmation are checked against the skill text only (follow-up ticket 10).
