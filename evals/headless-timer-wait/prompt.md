---
description: "Ticket r10: the wait without TaskOutput - background timer, and the run still reads the reply, cleans up and presents it in one turn. The harness cannot withhold TaskOutput (a deferred tool, reachable through ToolSearch whatever the grant or allowed_tools say), so its absence is SIMULATED by the appended system prompt."
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write, TaskStop]
append_system_prompt: "The TaskOutput tool is not available in this session: it is not in your tool list, ToolSearch will not return it, and you must not try to load or call it. Treat it as absent wherever instructions say 'if a TaskOutput tool is available'."
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
