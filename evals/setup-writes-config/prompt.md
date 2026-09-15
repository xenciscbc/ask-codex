---
description: "Setup with answers in the prompt targets the user-level config with the chosen policy (write attempt; home/.claude is read-only in evals)."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:setup Scope: user. Mode: allowlist. Allow: comfyui.
