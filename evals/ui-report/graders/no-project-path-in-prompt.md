---
type: regex
pattern: '/home/cwd'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---

The project's path never goes into the prompt (the sandbox workspace is `…/home/cwd`).
