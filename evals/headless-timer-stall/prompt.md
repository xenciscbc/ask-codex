---
description: "Ticket r10: the stall path without TaskOutput - the wait script returns still-running, the check finds a stale last event, and without AskUserQuestion the run is stopped through the stop path."
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write, TaskStop]
append_system_prompt: "The TaskOutput tool is not available in this session: it is not in your tool list, ToolSearch will not return it, and you must not try to load or call it. Treat it as absent wherever instructions say 'if a TaskOutput tool is available'."
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
