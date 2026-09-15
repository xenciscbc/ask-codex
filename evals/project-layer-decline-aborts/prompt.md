---
description: "Rule (c) hit and the user declines project-defined servers up front: abort, zero codex calls."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out? If this project's own Codex config defines any MCP servers, I decline them.
