---
description: "Review skill, --base main on a branch: one Codex call whose prompt names main and the branch's changed files, not a file only main changed."
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:review --base main
