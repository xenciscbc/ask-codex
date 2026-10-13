#!/usr/bin/env bash
# Guards for the approval-boundary live acceptance (plan.md). Usage: bash guard.sh <label> <evidence-dir>
# Records hashes of the user's Codex config.toml and the whole rules directory, backs up their bytes once,
# checks that ask-codex.json is absent, and records the codex* PID set.
label=$1
out=$2
mkdir -p "$out/guards"
if [ ! -e "$out/guards/backup" ]; then
  mkdir -p "$out/guards/backup/rules"
  cp /d/codex/config.toml "$out/guards/backup/config.toml"
  cp -r /d/codex/rules/. "$out/guards/backup/rules/"
fi
{
  sha256sum /d/codex/config.toml
  find /d/codex/rules -type f -print0 | sort -z | xargs -0 sha256sum
  if [ -e /c/Users/admin/.claude/ask-codex.json ]; then echo "ask-codex.json PRESENT"; else echo "ask-codex.json absent"; fi
} > "$out/guards/$label.txt"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -match '^codex' } | ForEach-Object { \$_.ProcessId } | Sort-Object" > "$out/guards/$label-pids.txt"
cat "$out/guards/$label.txt"
echo "pids: $(wc -l < "$out/guards/$label-pids.txt")"
