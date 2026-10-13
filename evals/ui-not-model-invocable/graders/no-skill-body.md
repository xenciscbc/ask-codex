---
type: regex
pattern: 'ask-codex-ui-skill-body'
match: not_contains
target: trace
---

The ui skill's body (marker `<!-- ask-codex-ui-skill-body -->`) never enters the session through a Skill-tool load; `disable-model-invocation: true` must keep the model from loading it.
