---
description: "Ticket r10: the wait without TaskOutput - the wait goes through the foreground wait script, and the run still reads the reply, cleans up and presents it in one turn. The harness cannot withhold TaskOutput (a deferred tool, reachable through ToolSearch whatever the grant or allowed_tools say), so its absence is SIMULATED by the appended system prompt (which calls the tool broken rather than absent: a model that finds it through ToolSearch does not believe 'absent' - 3 of 10 runs held with that wording)."
max_turns: 40
timeout_seconds: 1200
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write, TaskStop]
append_system_prompt: "In this session the TaskOutput tool is broken: calling it, or loading it with ToolSearch, ends the session at once and every piece of work is lost. Never call or load it. Wherever instructions say 'if a TaskOutput tool is available', treat it as NOT available and take the other branch."
---

/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?
