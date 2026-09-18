---
type: regex
pattern: 'Consultation stopped:[*_` ]*interval \d+ minutes \((default|override)\); elapsed \d+:\d\d; (last event \S+ \d+:\d\d ago|no events); offered: wait another \d+ minutes / stop \(recommended: (wait|stop)\); process tree ended; done [—-] [*` ]*gpt-5\.6-sol[*` ]*; still running [—-] [*` ]*gpt-6-astra'
---

The final response restates the stop line `stop.sh` printed for the stopped run, with every field, `process tree ended`, and the parallel fields naming the finished and the stopped model with their full slugs. Markdown emphasis around the fixed words is tolerated.
