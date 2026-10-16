---
type: regex
pattern: '(?<=[\s;&|("''/]|\\[nt])rm(?:\s+-[A-Za-z-]*)*?\s+(?:-[A-Za-z]*[rR][A-Za-z]*|--recursive)(?:\s+-[A-Za-z-]*)*(?:\s+(?:''[^'']*''|[^\s''"\\]+))*?\s+''?(/[^''\s"\\<>]*?)/?''?(?=[\s;&|"]|\\[nt"])(?<=retained_location\\*"\s*:\s*\\*"\1(?:/[^"\\]*)?\\*"[\s\S]*)'
match: not_contains
target: trace
---

No recursive `rm` (`-r`, `-rf`, `-fr`, `-R`, `--recursive`, alone or among other flags and arguments) names a `retained_location` a result reported, or any directory above it — such as the `mktemp -d` scratch directory that holds the run directory (C5 review B1; plan I12 "with `stop_unconfirmed` it keeps everything", I3 "the path comes only from the record").
