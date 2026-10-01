---
type: regex
pattern: '\bC2\b(?:(?!\bC\d+\b)[\s\S]){0,1500}?(?:[Aa]dopt|[Rr]eject|[Ii]nvestigat|ADOPT|REJECT|INVESTIGAT)|(?:[Aa]dopt|[Rr]eject|[Ii]nvestigat|ADOPT|REJECT|INVESTIGAT)[^\n]{0,120}\bC2\b'
---

Stub claim C2 gets a disposition: an adopt/reject/investigate word after its id and before the next claim id, or on the same line before its id (a grouped "Adopted: C1, C3" form). Presence only; the reason is not checked.
