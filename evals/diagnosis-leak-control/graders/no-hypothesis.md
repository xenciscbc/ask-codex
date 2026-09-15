---
type: regex
pattern: '[Aa]uthori[sz]ation|[Aa]uth(entication)? +[Hh]eader'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
