---
type: regex
pattern: '"name":"Write","input":\{[^\n]*claude-round-1\.md[\s\S]*"name":"Bash","input":\{[^\n]*(?:\\n|\b)rm\b[^\n]*claude-round-1\.md'
target: trace
---

Claude's round-1 file is written and then removed with a command that names it. In the trace a command's earlier lines end in a literal `\n`, so `rm` on a later line follows the letter `n` with no word boundary: the pattern accepts `\n` before `rm`.
