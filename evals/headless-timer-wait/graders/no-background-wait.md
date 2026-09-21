---
type: tool_used
tool: Bash
input_match: '(?=.*(?:scripts/wait\.sh|"command"\s*:\s*"sleep\s+[0-9]+))(?=.*"run_in_background"\s*:\s*true)'
min: 0
max: 0
---

Neither the wait script nor a bare `sleep` timer may be started in the background
(`run_in_background: true`): the wait has to block in the foreground, or the turn would end
while Codex is still running.
