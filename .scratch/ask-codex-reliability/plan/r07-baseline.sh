#!/usr/bin/env bash
# Ticket 07: are the below-1.00 cases regressions of today's skill edits or older flakes?
# Runs the same cases three times on the bytes of e2e8390 (before tickets 05 and 08), from a
# detached worktree at D:/tmp/ask-codex-wt-base — the main working tree is not touched.
#   bash .scratch/ask-codex-reliability/plan/r07-baseline.sh
BASE_WSL=/mnt/d/tmp/ask-codex-wt-base
echo "baseline $(git -C D:/tmp/ask-codex-wt-base rev-parse --short HEAD); start $(date +%H:%M:%S)"
for c in project-layer-aborts-01 project-env-redefined project-config-table pre-confirm-mismatch project-layer-decline-aborts followup-new-blocking; do
  echo "=== $c x3 (baseline e2e8390)"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i $BASE_WSL/evals/_harness/run-evals.sh --case "$c" --runs 3 --model claude-sonnet-5 --allow-tools Bash Write TaskOutput TaskStop 2>&1 \
    | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗'
done
echo "end $(date +%H:%M:%S)"
