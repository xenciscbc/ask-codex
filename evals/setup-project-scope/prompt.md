---
description: "Setup with project scope targets .claude/ask-codex.local.json with the chosen policy (write attempt; .claude/ is protected in evals)."
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

/ask-codex:setup Scope: project. Mode: allowlist. Allow: comfyui. Then consult Codex: why does fetchUser in src/user.js return an empty object when the API times out? I confirm this project's ask-codex config .claude/ask-codex.local.json, which allows the MCP server comfyui.
