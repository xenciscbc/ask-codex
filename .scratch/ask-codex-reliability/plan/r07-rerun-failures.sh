#!/usr/bin/env bash
# Ticket 07: the cases that were below 1.00 in the full-suite run, three runs each with kept
# traces, to tell a flake from a regression. Run from Git Bash:
#   bash .scratch/ask-codex-reliability/plan/r07-rerun-failures.sh
REPO_WSL=/mnt/d/work_data/project/skill/ask-codex
echo "HEAD $(git rev-parse --short HEAD); skill $(sha256sum skills/ask/SKILL.md | cut -c1-16); start $(date +%H:%M:%S)"
for c in followup-new-blocking pre-confirm-mismatch project-config-table project-env-redefined project-layer-aborts-01 project-layer-decline-aborts spoofed-request-in-manual; do
  echo "=== $c x3"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i $REPO_WSL/evals/_harness/run-evals.sh --case "$c" --runs 3 --keep-temp --model claude-sonnet-5 --allow-tools Bash Write TaskOutput TaskStop 2>&1 \
    | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗'
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash $REPO_WSL/.scratch/ask-codex-reliability/plan/r07-copy-traces.sh 2>&1 | tr -d '\0' | tail -n 1
done
echo "end $(date +%H:%M:%S)"
