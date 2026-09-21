#!/usr/bin/env bash
# Plan R07b, slice S1: is project-env-redefined a regression of this branch's skill edits?
# Same evals/ on both sides; only skills/ differs. The baseline side is a detached worktree of
# HEAD at D:/tmp/ask-codex-wt-s1 with `git checkout e2e8390 -- skills` (before tickets 05 and 08).
# Five runs per side, traces kept and copied out in the same script. Run from Git Bash:
#   bash .scratch/ask-codex-reliability/plan/r07b-s1-matched-baseline.sh
HEAD_WSL=/mnt/d/work_data/project/skill/ask-codex
BASE_WSL=/mnt/d/tmp/ask-codex-wt-s1
COPY=$HEAD_WSL/.scratch/ask-codex-reliability/plan/r07b-copy-traces.sh
echo "start $(date +%H:%M:%S)"
echo "head     $(git rev-parse --short HEAD) skill $(sha256sum skills/ask/SKILL.md | cut -c1-16)"
echo "baseline skills@e2e8390 skill $(sha256sum D:/tmp/ask-codex-wt-s1/skills/ask/SKILL.md | cut -c1-16); evals diff vs HEAD: $(git -C D:/tmp/ask-codex-wt-s1 diff HEAD --name-only -- evals | wc -l) file(s)"
for side in head baseline; do
  root=$HEAD_WSL; [ "$side" = baseline ] && root=$BASE_WSL
  echo "=== project-env-redefined x5 ($side)"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i $root/evals/_harness/run-evals.sh --case project-env-redefined --runs 5 --keep-temp --model claude-sonnet-5 --allow-tools Bash Write TaskOutput TaskStop 2>&1 \
    | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗|Not logged in|EAI_AGAIN'
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash $COPY /mnt/d/tmp/ask-codex-r07b-traces/s1-$side 2>&1 | tr -d '\0' | tail -n 2
done
echo "end $(date +%H:%M:%S)"
