---
type: tool_used
tool: Bash
input_match: 'scripts/wait\.sh'
min: 1
---

Without `TaskOutput`, step 8 waits by calling the shipped wait script in the foreground
(`bash '<skill dir>/scripts/wait.sh' '<tmp>' --seconds <n>`) instead of starting a background
timer and waiting for a notification.
