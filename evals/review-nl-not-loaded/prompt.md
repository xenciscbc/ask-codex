---
description: "Review skill is user-only: a natural-language request for it never loads it (no skill-body marker in the trace, no review prompt sent); the reply points to /ask-codex:review. An ask consultation of an existing type is allowed."
runs: 5
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

use the ask-codex review skill to review my uncommitted changes
