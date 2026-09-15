---
description: "F9: a model token with shell metacharacters is rejected, zero codex calls."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask sol;touch${IFS}pwned Why does fetchUser in src/user.js return an empty object when the API times out?
