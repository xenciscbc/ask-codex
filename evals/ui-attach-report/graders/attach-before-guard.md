---
type: regex
pattern: '\"name\":\"Bash\",\"input\":\{\"command\":\"(?:[^\"\\]|\\.)*?consult\.py''?\s+attach-start\s[\s\S]*\"name\":\"Bash\",\"input\":\{\"command\":\"(?:[^\"\\]|\\.)*?consult\.py''?\s+guard\s'
target: trace
---

attach-start runs before the guard (N-c: the supervisor polls the attached servers while the guard and the real-definition check run).
