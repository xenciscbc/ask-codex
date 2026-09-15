---
description: "Targeted check: the concern reaches Codex verbatim, without a general review request."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:ask Check one concern in src/user.js: does fetchUser swallow errors other than TimeoutError?
