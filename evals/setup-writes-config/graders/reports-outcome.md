---
type: llm
---

The user ran ask-codex setup with: scope user, allowlist mode, allow comfyui. In this environment the user-level config location may be read-only.
PASS if the final response states the target file (the user-level `.claude/ask-codex.json`) and the chosen policy (allowlist, comfyui), and either confirms it was written or clearly says it could not be written and why.
FAIL if the response claims success while also reporting a write error, writes a different scope's file, or does not mention the file.
