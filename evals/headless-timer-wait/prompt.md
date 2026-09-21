---
description: "Ticket r10: no TaskOutput - the wait goes through the background timer, and the run still reads the reply, cleans up and presents it in one turn."
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write, TaskStop]
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
