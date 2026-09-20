#!/usr/bin/env bash
# Ticket 07: the whole suite once, at HEAD with a clean tree, sandboxes kept so that a failing
# run's trace can be read (tickets 09 and 10). Run from Git Bash on Windows:
#   bash .scratch/ask-codex-reliability/plan/r07-full-suite.sh
# Traces are copied out of WSL /tmp right after the run (WSL wipes /tmp when idle) to
# D:/tmp/ask-codex-r07-traces — outside the repo; only the ones that matter get committed later.
REPO_WSL=/mnt/d/work_data/project/skill/ask-codex
echo "HEAD $(git rev-parse --short HEAD); dirty files: $(git status --short | wc -l); skill $(sha256sum skills/ask/SKILL.md | cut -c1-16); start $(date +%H:%M:%S)"
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i $REPO_WSL/evals/_harness/run-evals.sh --runs 1 --keep-temp --model claude-sonnet-5 --allow-tools Bash Write TaskOutput TaskStop 2>&1 \
  | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗|^[a-z0-9-]+ +[0-9.]+ +[0-9]+%|case\(s\)|Not logged in|^Report'
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash $REPO_WSL/.scratch/ask-codex-reliability/plan/r07-copy-traces.sh 2>&1 | tr -d '\0' | tail -n 2
echo "HEAD $(git rev-parse --short HEAD); dirty files: $(git status --short | wc -l); skill $(sha256sum skills/ask/SKILL.md | cut -c1-16); end $(date +%H:%M:%S)"
