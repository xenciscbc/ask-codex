#!/usr/bin/env bash
# Plan R07b: run named cases N times each with kept traces, copying the traces out after every case
# (WSL wipes /tmp when it idles). Run from Git Bash at the repo root:
#   bash .scratch/ask-codex-reliability/plan/r07b-run-cases.sh <segment> <runs> <case> [<case> …]
# Traces land in D:\tmp\ask-codex-r07b-traces\<segment>-<case>. TaskOutput is granted; the
# no-TaskOutput case of ticket 10 has its own runner.
seg="${1:?segment}"; runs="${2:?runs}"; shift 2
REPO_WSL=/mnt/d/work_data/project/skill/ask-codex
echo "HEAD $(git rev-parse --short HEAD); dirty $(git status --porcelain | wc -l); skill $(sha256sum skills/ask/SKILL.md | cut -c1-16); start $(date +%H:%M:%S)"
for c in "$@"; do
  echo "=== $c x$runs"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i $REPO_WSL/evals/_harness/run-evals.sh --case "$c" --runs "$runs" --keep-temp --model claude-sonnet-5 --allow-tools Bash Write TaskOutput TaskStop 2>&1 \
    | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗|Not logged in|EAI_AGAIN'
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash $REPO_WSL/.scratch/ask-codex-reliability/plan/r07b-copy-traces.sh "/mnt/d/tmp/ask-codex-r07b-traces/$seg-$c" 2>&1 | tr -d '\0' | tail -n 2
done
echo "end $(date +%H:%M:%S)"
