---
type: regex
pattern: 'ask-codex-discuss-skill-body'
match: not_contains
target: trace
---

The discuss skill's body (its marker line `<!-- ask-codex-discuss-skill-body -->`) never enters the session; `disable-model-invocation: true` must keep a Skill-tool load from happening.
