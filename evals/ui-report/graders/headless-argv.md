---
type: regex
pattern: '(?=[\s\S]*--headless)(?=[\s\S]*--userDataDir=)'
target:
  source: file
  path: .stub/exec-argv.json
---

Without --headed the browser server runs headless.
