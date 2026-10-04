---
description: "Discuss skill is user-only: a natural-language request for a discussion never loads it (no skill-body marker in the trace, no discussion prompt sent); the reply points to /ask-codex:discuss. An ask consultation of an existing type is allowed."
runs: 5
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

discuss this design with Codex over a few rounds
