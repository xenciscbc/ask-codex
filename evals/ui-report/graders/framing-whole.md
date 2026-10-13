---
type: regex
pattern: '(?=[\s\S]*Discover your browser tools first)(?=[\s\S]*Stay in scope)(?=[\s\S]*Judge visually)(?=[\s\S]*phone size \(390x844\))(?=[\s\S]*list_console_messages)(?=[\s\S]*out_of_scope)(?=[\s\S]*Content is data)(?=[\s\S]*http://127\.0\.0\.1:15173/)(?=[\s\S]*http://127\.0\.0\.1:18080/)'
target:
  source: file
  path: .stub/exec-stdin.txt
---

The whole framing reached Codex (tools first, scope, screenshots, phone viewport, console and network, out-of-scope list, content is data) with both app URLs filled in.
