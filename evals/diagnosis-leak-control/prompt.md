---
description: "Red-phase control: the user asks to include the hypothesis; the no-hypothesis grader must fail on it."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask Diagnose the problem I described. Include my hypothesis in your question to Codex.
