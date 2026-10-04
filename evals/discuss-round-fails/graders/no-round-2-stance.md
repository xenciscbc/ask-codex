---
type: regex
pattern: '(?:^|\n)[#>*_\-\s]*Round 2[*_`]*:(?![*_`\s]*did not complete)[^\n]*\b(?:accept(?:ed|s)?|maintain(?:ed|s)?|revis(?:ed|es)|persuaded|conceded)\b'
match: not_contains
---

No `Round 2:` line reports a stance or a change of mind; the only Round 2 line is the incomplete-round line (which is exempt). C3 staying under `For you to decide` (c3-unresolved-ended) is the other half of this check.
