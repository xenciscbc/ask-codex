---
type: regex
pattern: 'User call proposed by Claude: [^<\s]'
target:
  source: file
  path: .stub/exec-stdin.2.txt
---

Precondition: Claude did mark one of its own points as a user call, so round 2's prompt carries a proposal line with a real reason after the colon. The framing and the template name the line too (`User call proposed by Claude: <reason>`, `User call proposed by …`), so only a line whose reason does not start with `<` counts.
