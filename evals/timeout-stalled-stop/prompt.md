---
description: "timeout-stalled-stop"
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write, TaskOutput, TaskStop]
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
