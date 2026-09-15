---
description: "Probe (no skill): can a scaffold seed the throwaway Codex home, and can the agent read it?"
max_turns: 30
timeout_seconds: 900
allowed_tools: [Bash, Read]
---

Run `printenv HOME`, then Read the file `.codex/models_cache.json` inside that home directory and reply with only the slug of the model whose priority is 4.
