---
type: regex
pattern: 'Discussion round: (?:1 \(independent\)|follow-up)\.'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---

No prompt sent to Codex carries a discussion framing marker.
