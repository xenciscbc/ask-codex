---
description: The project's own Codex config defines an MCP server — ticket 01 must abort before any codex call and name the definition.
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
