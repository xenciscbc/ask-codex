---
description: "Probe (no skill): does case.yaml execution.env reach the agent's Bash commands?"
max_turns: 30
timeout_seconds: 900
allowed_tools: [Bash]
---

Run `printenv EVAL_CODEX_STUB_MODE; codex --version; echo exit=$?` and reply with the command output verbatim.
