#!/usr/bin/env bash
# Runs INSIDE WSL after the full-suite run: copy every kept trace to D:\tmp (outside the repo),
# named by sandbox id, then delete the kept sandboxes. Literal paths only.
dest=/mnt/d/tmp/ask-codex-r07-traces
mkdir -p "$dest"
n=0
for d in /tmp/ask-codex-eval.*/tmp/claude-eval-*; do
  [ -d "$d" ] || continue
  chmod 700 "$d" 2>/dev/null
  t="$(find "$d" -maxdepth 3 -name trace.jsonl 2>/dev/null | head -n 1)"
  [ -n "$t" ] || continue
  n=$((n + 1))
  cp "$t" "$dest/$(basename "$d").jsonl"
done
echo "copied $n trace(s) to $dest"
for top in /tmp/ask-codex-eval.*; do
  [ -d "$top" ] || continue
  chmod -R u+rwx "$top" 2>/dev/null
  rm -rf "$top"
done
echo "kept sandboxes left: $(ls -d /tmp/ask-codex-eval.* 2>/dev/null | wc -l)"
