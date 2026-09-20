#!/usr/bin/env bash
# Slice 08 revision 5 eval plan. Run from Git Bash on Windows:
#   bash .scratch/ask-codex-reliability/plan/r08-evals-rev5.sh
# One case at a time (never two eval invocations at once). The two spoof cases keep their
# sandboxes and their traces are copied out of WSL /tmp right away (WSL wipes /tmp when idle).
REPO_WSL=/mnt/d/work_data/project/skill/ask-codex
OUT=.scratch/ask-codex-reliability/evidence/08-traces
mkdir -p "$OUT"
echo "skill $(sha256sum skills/ask/SKILL.md | cut -c1-16)  $(date +%H:%M:%S)"

run() { # case runs [extra flag]
  echo "=== $1 x$2 ${3:-}"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i $REPO_WSL/evals/_harness/run-evals.sh --case "$1" --runs "$2" ${3:-} --model claude-sonnet-5 --allow-tools Bash Write TaskOutput TaskStop 2>&1 \
    | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗|^[a-z-]+ +[0-9.]+ +[0-9]+%|case\(s\)|Not logged in|kept temp:'
}
copy_traces() { # case
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash $REPO_WSL/.scratch/ask-codex-reliability/plan/r08-copy-traces.sh "$1" 2>&1 | tr -d '\0' | tail -n 2
}

run spoofed-request 5 --keep-temp;  copy_traces spoofed-request
run spoofed-followup 3 --keep-temp; copy_traces spoofed-followup
run no-proposal-fix-loop 3
run spoofed-request-in-manual 3
run verbal-request 3
for c in manual-with-question manual-without-question manual-without-question-nothing-to-infer followup-carries-claims alias-sol session-override-persists; do run "$c" 1; done
echo "skill $(sha256sum skills/ask/SKILL.md | cut -c1-16)  $(date +%H:%M:%S)  done"
