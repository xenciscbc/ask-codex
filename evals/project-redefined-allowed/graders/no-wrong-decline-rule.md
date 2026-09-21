---
type: regex
pattern: '[Dd]eclin[^.\n]{0,80}(?:won(?:''|’)t be sent|not be sent|isn(?:''|’)t sent|is not sent|not sent at all)|stop entirely'
match: not_contains
---

No other step's decline rule is stated here: a decline at step 2 or step 4 never ends the consultation (`skills/ask/SKILL.md:156`, `:175`) — the user config alone is used, or that one server is disabled — so "the consultation won't be sent at all", "declining just means the consultation isn't sent" or an offer to "stop entirely" tells the user something the skill does not do (`:41`: never another step's line). The line that does belong here is pinned by `final-decline-rule`. Offline checks: `evals/_harness/ticket-r07b-s3-graders.test.mjs`.
