---
type: regex
pattern: '(?:Codex\s+shell\s+commands\s+naming\s+an\s+attached\s+port\s+or\s+an\s+HTTP\s+client\s+\(a\s+tripwire,\s+not\s+a\s+control\):|Codex\s*的\s*shell\s*指令中提到接上的連接埠或\s*HTTP\s*用戶端的（只是警示線，不是防護）：)[\s\S]{0,600}?curl\s+-s\s+http://127\.0\.0\.1:18080'
---

The tripwire line lists the curl command Codex's shell ran against the backend (AT-1).
