---
type: regex
pattern: 'mcp_servers\.(blender|node_repl|pencil|cua_repl)=\{\s*command\s*=\s*\\"ask-codex-disabled\\"\s*,\s*enabled\s*=\s*false\s*\}'
match: "count:4"
target:
  source: file
  path: .stub/exec-argv.json
---
