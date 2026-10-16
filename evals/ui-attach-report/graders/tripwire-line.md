---
type: regex
pattern: '(?:^|\n)[-*_\x60 \t]*(?:Codex\s+shell\s+commands\s+naming\s+an\s+attached\s+port\s+or\s+an\s+HTTP\s+client\s+\(a\s+tripwire,\s+not\s+a\s+control\):|Codex\s*的\s*shell\s*指令中提到接上的連接埠或\s*HTTP\s*用戶端的（只是警示線，不是防護）：)[\s\S]{0,600}?curl\s+-s\s+http://127\.0\.0\.1:18080'
---

The tripwire line, copied from the table's `tripwire` row with its fixed words unchanged and no label before them (C8 fix E1), lists the curl command that named the backend's port (AT-1). A list marker or Markdown emphasis before the line is allowed; words are not.
