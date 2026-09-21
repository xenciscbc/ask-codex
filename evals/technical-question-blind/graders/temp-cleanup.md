---
type: regex
pattern: '/ask-codex/(run\.(?!XXXXXX)[A-Za-z0-9]{6})(?=\\n|")(?![\s\S]*rm\s+-rf\s+(?:--\s+)?(?:''[^'']*''\s+)*''[^'']*/ask-codex/\1'')'
match: not_contains
target: trace
---

Every run directory the run created is deleted again (step 11). The pattern finds a directory name as `mktemp -d` printed it — the bare name at the end of an output line, never the template `run.XXXXXX` — that no later `rm -rf -- '<…>/ask-codex/<same name>'` names (one `rm` may name several directories); finding one fails the run. A run that stopped before step 1 created nothing and passes. It checks that the command was issued for each directory, not that the directory is gone: the run directory lies outside the workspace, where no grader can look. Identical in every case; offline checks in `evals/_harness/ticket-r07-graders.test.mjs`.
