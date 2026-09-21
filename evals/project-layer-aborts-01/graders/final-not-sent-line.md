---
type: regex
pattern: '(?:^|\n)[\s*_>#]*Consultation not sent — confirmation needed\.'
---

The final message carries the fixed line `Consultation not sent — confirmation needed.` word for word and on a line of its own (`skills/ask/SKILL.md:41`), so a user who sees only the last message reads there that nothing was sent; one lead-in sentence may come before it and markdown emphasis or a quote mark may open the line, but the words must start a line — buried inside a sentence they do not count.
