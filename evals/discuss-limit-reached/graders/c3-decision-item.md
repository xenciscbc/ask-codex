---
type: regex
pattern: 'For you to decide[\s\S]*?\bC3\b(?:(?!\bC\d+\b)[\s\S])*?Claude recommends[*_`]*:(?:(?!\bC\d+\b)[\s\S])*?Codex recommends[*_`]*:'
---

After the heading `For you to decide`, C3 is named and, before any other C id, both a `Claude recommends:` and a `Codex recommends:` line follow.
