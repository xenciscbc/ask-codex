---
type: regex
pattern: '\b10[ -]?(s|secs?|seconds?)\b|[Rr]etr(y|ies|ied)'
target:
  source: file
  path: .stub/exec-stdin.txt
---
