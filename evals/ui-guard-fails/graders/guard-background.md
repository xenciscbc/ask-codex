---
type: tool_used
tool: Bash
input_match: '(?=.*consult\.py''?\s+guard\s[^"]*--result\s)(?=.*"run_in_background"\s*:\s*true)'
min: 1
---

The guard runs in the background with a result file (a long operation).
