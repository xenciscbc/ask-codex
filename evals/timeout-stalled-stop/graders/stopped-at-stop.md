---
type: regex
pattern: '"role":"assistant"[^\n]*Consultation stopped:[^\n]*process tree ended[\s\S]*"name":"TaskStop"'
target: trace
---

The stop report is written by the assistant itself at the moment of the stop, before the `TaskStop` call — not only restated in the final reply. The trace holds one JSON message per line: the assistant's own messages carry `"role":"assistant"`, tool results (including `stop.sh`'s stdout, which contains the same line) carry `"role":"user"`. Anchoring `"role":"assistant"` and the fixed words on the same line therefore accepts only a line the model wrote; the JSON encoding keeps each message on one line, so `[^\n]*` stays inside it. Only the real call matches `"name":"TaskStop"`.
