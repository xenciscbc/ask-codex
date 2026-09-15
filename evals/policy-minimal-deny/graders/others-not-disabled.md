---
type: regex
pattern: 'mcp_servers\.(blender|comfyui|pencil)='
match: not_contains
target:
  source: file
  path: .stub/exec-argv.json
---
