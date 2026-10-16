---
type: regex
pattern: '(?:This\s+exercise\s+used\s+your\s+dev\s+data:\s+it\s+may\s+have\s+written\s+outside\s+the\s+disposable\s+target,\s+and\s+network\s+bodies\s+with\s+that\s+data\s+may\s+have\s+reached\s+OpenAI\.|本次演練使用了你的\s*dev\s*資料：它可能已在可丟棄目標之外寫入，含這些資料的網路內容也可能已送到\s*OpenAI。)'
match: not_contains
---

Attach mode has no dev-data line: DS-ATTACH says it.
