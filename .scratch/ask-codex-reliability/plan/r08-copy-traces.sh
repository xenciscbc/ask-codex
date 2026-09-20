#!/usr/bin/env bash
# Runs INSIDE WSL: copy every kept eval trace to the repo's evidence directory, then delete the
# kept sandboxes. Literal paths only (shell variables passed through `wsl … bash -c` arrive empty).
#   bash r08-copy-traces.sh <case name>
case_name="$1"
dest=/mnt/d/work_data/project/skill/ask-codex/.scratch/ask-codex-reliability/evidence/08-traces
mkdir -p "$dest"
n=0
for d in /tmp/ask-codex-eval.*/tmp/claude-eval-*; do
  [ -d "$d" ] || continue
  chmod 700 "$d" 2>/dev/null
  t="$(find "$d" -maxdepth 3 -name trace.jsonl 2>/dev/null | head -n 1)"
  [ -n "$t" ] || continue
  n=$((n + 1))
  cp "$t" "$dest/$case_name-$(basename "$d").jsonl"
done
echo "copied $n trace(s) for $case_name"
for top in /tmp/ask-codex-eval.*; do
  [ -d "$top" ] || continue
  chmod -R u+rwx "$top" 2>/dev/null
  rm -rf "$top"
done
echo "kept sandboxes left: $(ls -d /tmp/ask-codex-eval.* 2>/dev/null | wc -l)"
