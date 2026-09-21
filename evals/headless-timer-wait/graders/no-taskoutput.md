---
type: tool_used
tool: TaskOutput
min: 0
max: 0
---

This case withholds `TaskOutput` (it is not in the prompt's `allowed_tools`), so step 8's wait has to go through the background timer — the path of reliability ticket 10, which every other timer case skips because they are granted `TaskOutput`. A call here would mean the case no longer tests that path.
