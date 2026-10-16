---
description: "UI skill, attach mode, English: the user asked in this conversation to attach to the dev servers they run; Claude checks the owners with attach-owners and shows the attach-mode confirmation with DS-U8, DS-A7, DS-U7, DS-AT3, DS-AT6 and DS-AT10, the owners redacted, and starts nothing."
runs: 3
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ui the signup form
