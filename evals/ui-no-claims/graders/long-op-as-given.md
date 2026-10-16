---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?=(?:[^"\\]|\\.)*?consult\.py''?\s+(?:guard|app-start|finish|stop|run)\s)(?=(?:[^"\\]|\\.)*?(?:(?<![&>|])&(?![&>])|(?<=["\s;&|(]|\\[nt])(?:disown|nohup)(?![\w-])))'
min: 0
max: 0
---

Every background launch (guard, app-start, finish, stop, run) is the command exactly as given: no shell `&`, `disown` or `nohup` (C5 review P1: a process sent to the background inside the `run_in_background` shell dies with it and `wait-result` reports `missing`). `&&`, `2>&1` and `&>` are no match.
