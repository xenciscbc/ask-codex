---
type: regex
pattern: '\\?"mode\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*\\?"attach\\?"(?:\s|\\[nrt])*[,}]'
match: not_contains
target: trace
---

No request ever names attach mode.
