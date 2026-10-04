---
type: regex
pattern: 'For you to decide[\s\S]*?\bC3\b(?:(?!\bC(?!3\b)\d+\b)[\s\S])*?Claude recommends[*_`]*:(?:(?!\bC(?!3\b)\d+\b)[\s\S])*?Codex recommends[*_`]*:'
---

After the heading `For you to decide`, C3 is named and, before any other C id, both a `Claude recommends:` and a `Codex recommends:` line follow. C3 itself may be mentioned again inside its recommendations (a t02b reply did).
