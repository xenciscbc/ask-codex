---
type: regex
pattern: 'Consultation type: review\.'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---

No prompt sent to Codex carries the review framing. The scaffold creates the file empty (a regex grader fails on a missing file); with at most one call (`at-most-one-call`) it holds every prompt that was sent.
