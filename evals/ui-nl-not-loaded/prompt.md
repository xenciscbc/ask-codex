---
description: "UI skill is user-only: a natural-language request for Codex to test the UI is answered by naming /ask-codex:ui only: no exercise, no consultation in its place, no skill-body load."
runs: 5
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

Have Codex click through the signup form of this app in a browser and tell me what's broken.
