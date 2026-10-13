---
description: "UI skill, English: the target root comes from the user's earlier message; Claude checks the dependencies, works out the app from the README and shows the confirmation with DS-U8, DS-A7 and the codex-cli version line, then stops (headless) with nothing prepared."
runs: 3
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ui the signup form
