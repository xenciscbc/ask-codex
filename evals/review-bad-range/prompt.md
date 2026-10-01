---
description: "Review skill, a range whose endpoint is an option (main..--output=x): rejected before any Codex command; no sentinel, no file x."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:review main..--output=x
