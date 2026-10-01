---
description: "Review skill, model token + commit range + focus: one Codex call on the resolved sol slug; the prompt names both range endpoints and carries the focus verbatim."
max_turns: 40
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:review sol main..HEAD check error handling
