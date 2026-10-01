#!/usr/bin/env bash
# codex-review: fingerprinted eval runner (adapted from ask-codex-reliability/plan/r07b-run-logged.sh).
# Run from Git Bash at the main repo root:
#   bash .scratch/codex-review/run-logged.sh <segment> <repo-root-gitbash-path> <case>:<runs> [...]
# <repo-root> is the checkout whose evals run (the main repo, or a baseline worktree under /d/tmp).
# Log: .scratch/codex-review/evidence/<segment>-run-log.txt in the main repo (appended).
# Traces: D:\tmp\ask-codex-r07b-traces\review-<segment>-<case>.
seg="${1:?segment}"; root="${2:?repo root}"; shift 2
ALLOW="${R07B_ALLOW_TOOLS:-Bash Write TaskOutput TaskStop}"
case "$root" in
  /d/*) root_wsl="/mnt/d/${root#/d/}" ;;
  *) echo "repo root must be under /d" >&2; exit 2 ;;
esac
mkdir -p .scratch/codex-review/evidence
log=".scratch/codex-review/evidence/$seg-run-log.txt"
fingerprint() {
  echo "[$1 $(date '+%Y-%m-%d %H:%M:%S')] root $root HEAD $(git -C "$root" rev-parse HEAD)"
  for f in skills/ask/SKILL.md skills/review/SKILL.md; do
    [ -f "$root/$f" ] && echo "[$1] $f sha256 $(sha256sum "$root/$f" | cut -d' ' -f1)"
  done
  echo "[$1] git status --porcelain: $(git -C "$root" status --porcelain | grep -v -F 'codex-review/evidence/' | wc -l) line(s)"
  git -C "$root" status --porcelain | grep -v -F 'codex-review/evidence/' | sed 's/^/[status] /'
}
fingerprint before | tee -a "$log"
echo "[grant] --allow-tools $ALLOW" | tee -a "$log"
for spec in "$@"; do
  c="${spec%%:*}"; runs="${spec##*:}"
  echo "=== $c x$runs" | tee -a "$log"
  before="$(ls "$root/evals/results" 2>/dev/null | sort)"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash -i "$root_wsl/evals/_harness/run-evals.sh" --case "$c" --runs "$runs" --keep-temp --model claude-sonnet-5 --allow-tools $ALLOW 2>&1 \
    | tr -d '\0' | grep --line-buffered -E 'run [0-9]+/[0-9]+: score|✗|Not logged in|EAI_AGAIN' | tee -a "$log"
  comm -13 <(echo "$before") <(ls "$root/evals/results" | sort) | sed "s|^|results: $root/evals/results/|" | tee -a "$log"
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash /mnt/d/work_data/project/skill/ask-codex/.scratch/ask-codex-reliability/plan/r07b-copy-traces.sh "/mnt/d/tmp/ask-codex-r07b-traces/review-$seg-$c" 2>&1 | tr -d '\0' | tail -n 2 | tee -a "$log"
done
fingerprint after | tee -a "$log"
