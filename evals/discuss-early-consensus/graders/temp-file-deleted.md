---
type: regex
pattern: '"name":"Write","input":\{[^\n]*claude-round-1\.md[\s\S]*"name":"Bash","input":\{[^\n]*\brm\b[^\n]*claude-round-1\.md'
target: trace
---

Claude's round-1 file is written and then removed with a command that names it.
