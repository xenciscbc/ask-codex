---
description: "UI skill, no target root anywhere: Claude asks with the fixed line and stops (headless)."
runs: 3
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ui the signup form
