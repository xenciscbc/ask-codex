---
description: "Alias astra resolves to gpt-6-astra with effort medium; without AskUserQuestion the choice applies to this consultation only."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask astra Why does fetchUser in src/user.js return an empty object when the API times out?
