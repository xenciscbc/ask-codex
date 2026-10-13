---
description: "UI skill, target root suggested only by the project's CLAUDE.md: Claude asks with the fixed line naming the suggestion and uses nothing before the user answers (headless: the question is the closing message)."
runs: 5
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ui the signup form
