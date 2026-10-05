---
type: regex
pattern: 'unresolved because the discussion ended'
match: not_contains
---

A discussion that reached its round limit marks no item `unresolved because the discussion ended`; those words belong only to a discussion that ended on a round that could not complete (verifier finding F1, 2026-10-05: 4 of 6 limit-path reports on 3e7ec28 used them).
