---
type: tool_used
tool: TaskOutput
min: 0
max: 0
---

This case simulates TaskOutput's absence through the appended system prompt (commit `67f2dfa`; it is not withheld via `allowed_tools`, which the harness cannot do for a deferred tool), so step 8's wait has to go through the foreground wait script — the path of reliability ticket 10, which every other timer case skips because they are granted `TaskOutput`. A call here would mean the case no longer tests that path.
