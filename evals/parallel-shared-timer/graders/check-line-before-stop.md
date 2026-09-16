---
type: regex
pattern: 'Parallel check:[\s\S]*"name":"TaskStop"'
target: trace
---

The check line must be written at the check itself, before the run is stopped — not only in the
final reply. In the trace the assistant's text block precedes the tool_use block of the same
message, so a check line written before `TaskStop` appears earlier in the trace than the call.
Only a real call matches `"name":"TaskStop"` (the allowed-tools list and the ToolSearch query
mention the name in other shapes).
