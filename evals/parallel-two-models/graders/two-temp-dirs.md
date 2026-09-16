---
type: regex
pattern: 'mktemp -d'
match: "count:2"
target: trace
---

One run directory per model. Counted over the trace rather than over Bash calls: the skill never
says the two directories must be created in two separate commands, and a single command that
creates both is equally correct.
