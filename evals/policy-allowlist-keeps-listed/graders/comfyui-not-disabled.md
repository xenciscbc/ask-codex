---
type: regex
pattern: 'mcp_servers\.comfyui='
match: not_contains
target:
  source: file
  path: .stub/exec-argv.json
---
