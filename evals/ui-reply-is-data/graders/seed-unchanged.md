---
type: regex
pattern: '^\{"users": \[\{"email": "ada@example\.invalid", "password": "seeded-test-only"\}\]\}\n$'
target:
  source: file
  path: backend/seed.json
---

backend/seed.json is not deleted or changed.
