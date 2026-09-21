#!/usr/bin/env bash
# Plan R07b: like r07b-run-cases.sh, but every case has its own run count and the run is fingerprinted
# in a log the outcome verifier can read: HEAD, `git status --porcelain` and the SKILL.md sha256 before
# the first run and after the last, and every result directory produced in between.
# Run from Git Bash at the repo root, on a committed, clean tree:
#   bash .scratch/ask-codex-reliability/plan/r07b-run-logged.sh <segment> <case>:<runs> [<case>:<runs> …]
# Log: .scratch/ask-codex-reliability/evidence/07b-<segment>-run-log.txt (appended).
# Traces: D:\tmp\ask-codex-r07b-traces\<segment>-<case>. TaskOutput is granted.
seg="${1:?segment}"; shift
# Operator grant; R07B_ALLOW_TOOLS overrides it. The ticket-10 case needs a run WITHOUT TaskOutput: a
# case's own allowed_tools does not withhold a tool the operator granted (seen 2026-09-21, 5 of 5 runs).
ALLOW="${R07B_ALLOW_TOOLS:-Bash Write TaskOutput TaskStop}"
REPO_WSL=/mnt/d/work_data/project/skill/ask-codex
log=".scratch/ask-codex-reliability/evidence/07b-$seg-run-log.txt"
fingerprint() {
  echo "[$1 $(date '+%Y-%m-%d %H:%M:%S')] HEAD $(git rev-parse HEAD)"
  echo "[$1] SKILL.md sha256 $(sha256sum skills/ask/SKILL.md | cut -d' ' -f1)"
  echo "[$1] git status --porcelain (the run log itself excluded): $(git status --porcelain | grep -v -F "$log" | wc -l) line(s)"
  git status --porcelain | grep -v -F "$log" | sed 's/^/[status] /'
}
fingerprint before | tee -a "$log"
echo "[grant] --allow-tools $ALLOW" | tee -a "$log"
for spec in "$@"; do
  c="${spec%%:*}"; runs="${spec##*:}"
  echo "=== $c x$runs" | tee -a "$log"
  before="$(ls evals/results 2>/dev/null | sort)"
  # The spec `ALL:<runs>` runs the whole suite: no --case at all (a `*` could be glob-expanded on its way through wsl.exe).
  sel=(--case "$c"); [ "$c" = ALL ] && sel=()
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i $REPO_WSL/evals/_harness/run-evals.sh "${sel[@]}" --runs "$runs" --keep-temp --model claude-sonnet-5 --allow-tools $ALLOW 2>&1 \
    | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗|Not logged in|EAI_AGAIN' | tee -a "$log"
  comm -13 <(echo "$before") <(ls evals/results | sort) | sed 's|^|results: evals/results/|' | tee -a "$log"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash $REPO_WSL/.scratch/ask-codex-reliability/plan/r07b-copy-traces.sh "/mnt/d/tmp/ask-codex-r07b-traces/$seg-${c//\*/all}" 2>&1 | tr -d '\0' | tail -n 2
done
fingerprint after | tee -a "$log"
