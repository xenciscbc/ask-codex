---
type: tool_used
tool: Bash
input_match: '(?=.*consult\.py''?\s+app-start\s[^"]*--result\s)(?=.*"run_in_background"\s*:\s*true)'
min: 1
---

app-start runs in the background with a result file (C4 review item 30).
