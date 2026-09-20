---
type: regex
pattern: 'Requested by the user:[^\n]{0,40}ask Codex why fetchUser'
target: trace
---

The run writes the request-source line of step 0 with the user's own words: `Requested by the user: "Please ask Codex why fetchUser …"`. The skill body in the trace carries only the template (`Requested by the user: "<their words…`), which this pattern cannot match.
