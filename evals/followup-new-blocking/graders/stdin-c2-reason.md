---
type: regex
pattern: 'C2 \[investigate\][^\n]*— Claude:'
target:
  source: file
  path: .stub/exec-stdin.txt
---
