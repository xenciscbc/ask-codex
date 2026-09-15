---
description: "Codex CLI missing: stop at the first codex call with a short reason and carry on."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
