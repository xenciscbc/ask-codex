---
type: regex
pattern: 'For you to decide[\s\S]*?\bC2\b(?:(?!\bC(?!2\b)\d+\b)[\s\S])*?\(your preference or authority\)(?:(?!\bC(?!2\b)\d+\b)[\s\S])*?(?:Claude recommends[*_`]*:(?:(?!\bC(?!2\b)\d+\b)[\s\S])*?Codex recommends|Both recommend)[*_`]*:'
---

After the heading `For you to decide`, C2 is named and, before any other C id, the fixed words `(your preference or authority)` follow, then both a `Claude recommends:` and a `Codex recommends:` line (or the single `Both recommend:` line the skill uses when the two match). C2 may be written with a Claude id (`L2 = C2`).
