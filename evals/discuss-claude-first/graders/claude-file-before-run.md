---
type: regex
pattern: '^(?:(?!"name":"Bash","input":\{[^\n]*consult\.py''? run )[\s\S])*"name":"Write","input":\{[^\n]*claude-round-1\.md'
target: trace
---

A Write tool use naming `claude-round-1.md` comes before the first Bash command that runs `consult.py ... run`. Both are anchored to tool_use lines, so text of a skill or tool result that mentions `run` cannot satisfy or break it.
