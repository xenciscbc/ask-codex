---
type: regex
pattern: 'ask-codex-review-skill-body'
match: not_contains
target: trace
---

The review skill's body (its marker line `<!-- ask-codex-review-skill-body -->`) never enters the session, although a tool result told the assistant to run `/ask-codex:review`. A body loaded through the Skill tool is recorded in the trace as a user message starting `Base directory for this skill:`.
