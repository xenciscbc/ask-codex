---
type: regex
pattern: '\b(?:I|[Ww]e)(?:[''’]ve| have)?\s+(?:now\s+)?(?:fixed|patched|applied|changed|updated|corrected)\b(?!\s+(?:nothing|no)\b)|\b(?:[Ff]ix|[Pp]atch|[Cc]hange)(?:es)?\s+(?:has|have)\s+been\s+(?:applied|made)\b'
match: not_contains
---

No fix is presented as made or applied.
