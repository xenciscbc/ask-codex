---
type: regex
pattern: '(?:^|\n)[#>*_\-\s]*Round 2[*_`]*:[*_`]*\s*did not complete — [^\n]+\.[*_`]*[ \t]*(?:\r?\n|$)'
---

The process section has the fixed line for the incomplete round: `Round 2: did not complete — <reason>.` (markdown around `Round 2:` is tolerated).
