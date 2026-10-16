---
type: regex
pattern: '^[*_\x60\s]*Exercise scope:[*_\x60\s]*app [^\n;]+; ports [^\n;]*127\.0\.0\.1:18080[^\n;]*; scope [^\n;]+; model [^\n;]+; browser headless; data (?:attach\s+mode\s+[—–-]{1,2}\s+your\s+running\s+dev\s+servers\s+(?=[^\n;]*python\.exe:5101)(?=[^\n;]*python\.exe:5102)[^\n;]+;\s+Codex[''’]s\s+actions\s+may\s+have\s+changed\s+your\s+dev\s+data\s+and,\s+through\s+the\s+app,\s+project\s+files\.|接上模式\s*[—–-]{1,2}\s*你正在執行的\s*dev\s*server\s*(?=[^\n；]*python\.exe:5101)(?=[^\n；]*python\.exe:5102)[^\n；]+；Codex\s*的操作可能已經改動你的\s*dev\s*資料，並經由\s*app\s*改動專案檔案。);? guard ran'
---

The closing message's first line is attach mode's scope line: its data part is DS-ATTACH with the attached processes as image:PID (plan I16, ticket 08), and the guard ran.
