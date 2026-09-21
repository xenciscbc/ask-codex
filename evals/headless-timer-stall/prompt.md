---
description: "Ticket r10: the stall path without TaskOutput - the wait script returns still-running, the check finds a stale last event, and without AskUserQuestion the run is stopped through the stop path."
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write, TaskStop]
append_system_prompt: "In this session the TaskOutput tool is broken: calling it, or loading it with ToolSearch, ends the session at once and every piece of work is lost. Never call or load it. Wherever instructions say 'if a TaskOutput tool is available', treat it as NOT available and take the other branch."
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
