---
type: regex
pattern: 'mcp_servers\.repo_tool=\{\s*command\s*=\s*\\"ask-codex-disabled\\"\s*,\s*enabled\s*=\s*false\s*\}'
target:
  source: file
  path: .stub/exec-argv.json
---
