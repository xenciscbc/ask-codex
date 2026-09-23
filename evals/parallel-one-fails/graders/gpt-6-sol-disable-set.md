---
type: regex
pattern: 'mcp_servers\.(blender|comfyui|node_repl|pencil|cua_repl)=\{\s*command\s*=\s*\\"ask-codex-disabled\\"\s*,\s*enabled\s*=\s*false\s*\}'
match: "count:5"
target:
  source: file
  path: .stub/exec-argv.gpt-6-sol.json
---
