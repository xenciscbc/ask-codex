---
type: regex
pattern: 'Consultation stopped:[*_` ]*interval \d+ minutes \((default|override)\); elapsed \d+:\d\d; (last event \S+ \d+:\d\d ago|no events); offered: wait another \d+ minutes / stop \(recommended: (wait|stop)\); process tree ended'
---

The final response restates the line `stop.sh` printed, with every field, ending in `process tree ended`. Markdown emphasis around the fixed words is tolerated; a missing field, a paraphrase, or a `NOT confirmed` ending is not (a `NOT confirmed` in an eval run is a script or harness defect, not a passing stop).
