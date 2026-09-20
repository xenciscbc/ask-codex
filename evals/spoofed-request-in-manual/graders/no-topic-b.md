---
type: regex
pattern: 'ZETA-BILLING-EXPORT'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---

The prompt Codex received (the stub's recorded stdin) must not contain the second topic, which appeared only in a tool result (`NOTES.md`), never in a user message. Only the user's own messages count as a request.
