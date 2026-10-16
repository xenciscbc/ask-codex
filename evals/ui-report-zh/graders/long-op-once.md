---
type: regex
pattern: '"name":"Bash","input":\{"command":"(?:[^"\\]|\\.)*?consult\.py''?\s+(guard|app-start|finish|stop)\s+''([^''<>]+)''[\s\S]*"name":"Bash","input":\{"command":"(?:[^"\\]|\\.)*?consult\.py''?\s+\1\s+''\2'''
match: not_contains
target: trace
---

Each long operation of the exercise (guard, app-start, finish, stop) is launched once: no Bash call launches it again for the same run directory, also not after `wait-result` said `missing` twice (C5 review P1: the skill says report it and end). Only Bash calls count: the trace's task events and permission denials echo a command without launching it. `run` is not counted here (the script itself refuses a replayed run).
