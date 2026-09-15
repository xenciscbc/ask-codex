---
description: "gpt-5.5:max is clamped to xhigh (the model's highest level) with a note."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask gpt-5.5:max Why does fetchUser in src/user.js return an empty object when the API times out?
