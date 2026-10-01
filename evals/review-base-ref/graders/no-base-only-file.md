---
type: regex
pattern: 'README\.md'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---

Only main changed README.md after the branch point, so it is not part of the branch's change: the scope is `main...HEAD` (from the merge base), not `git diff main`.
