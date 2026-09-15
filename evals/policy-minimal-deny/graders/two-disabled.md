---
type: regex
pattern: 'mcp_servers\.(node_repl|cua_repl)=\{\s*command\s*=\s*\\"ask-codex-disabled\\"\s*,\s*enabled\s*=\s*false\s*\}'
match: "count:2"
target:
  source: file
  path: .stub/exec-argv.json
---
