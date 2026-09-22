#!/usr/bin/env bash
# ask-codex foreground wait (reliability ticket 10).
#
#   bash wait.sh <run directory> [<run directory> …] --seconds <n>
#
# Blocks in the foreground until EVERY named run directory has an `exit-code` file (written by
# run.sh when the launched command ends) or `<n>` seconds have passed, whichever comes first.
# File-based only: in the eval sandbox every Bash call is its own PID namespace, so a pid
# recorded by one call means nothing to a later one — `exit-code` is the only thing that
# survives across calls. Polls once a second (`sleep 1`); no busy loop, no `wait`/`kill -0` on
# pids.
#
# Prints exactly one line per run directory, in argument order, on stdout and nothing else:
#   finished exit=<code> <run directory>
#   still-running elapsed=<seconds>s <run directory>
# Exit status 0 in both cases; usage errors and a missing run directory print a message on
# stderr and exit 2.
#
# A directory can stay `still-running` for a reason other than "still running": run.sh may have
# been killed, or failed on a usage error before it ever launched the command, in either case
# without writing `exit-code`. This script cannot tell the two apart from a directory alone —
# that is accepted: `events.jsonl` then stops changing and the caller's own liveness check leads
# to the stop path one interval later.
set -u

if [ -x /usr/bin/uname ] && case "$(/usr/bin/uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) true ;; *) false ;; esac; then
  PATH="/usr/bin:/bin:$PATH"; export PATH
fi

usage() { echo "usage: wait.sh <run directory> [<run directory> …] --seconds <n>" >&2; exit 2; }

argv=("$@")
n=${#argv[@]}
[ "$n" -ge 3 ] || usage
[ "${argv[$((n-2))]}" = "--seconds" ] || usage
seconds="${argv[$((n-1))]}"

case "$seconds" in
  ''|*[!0-9]*) usage ;;
esac
[ "${seconds#0}" = "$seconds" ] || usage
[ "$seconds" -ge 1 ] && [ "$seconds" -le 570 ] || usage

dirs=("${argv[@]:0:$((n-2))}")
[ "${#dirs[@]}" -ge 1 ] || usage
for d in "${dirs[@]}"; do
  [ -d "$d" ] || { echo "wait.sh: run directory not found: $d" >&2; exit 2; }
done

started="$(date +%s)"
while :; do
  done_count=0
  for d in "${dirs[@]}"; do
    [ -e "$d/exit-code" ] && done_count=$((done_count + 1))
  done
  [ "$done_count" -eq "${#dirs[@]}" ] && break
  elapsed=$(( $(date +%s) - started ))
  [ "$elapsed" -ge "$seconds" ] && break
  sleep 1
done
elapsed=$(( $(date +%s) - started ))

for d in "${dirs[@]}"; do
  if [ -e "$d/exit-code" ]; then
    code="$(cat -- "$d/exit-code" 2>/dev/null)"
    echo "finished exit=${code} $d"
  else
    echo "still-running elapsed=${elapsed}s $d"
  fi
done
exit 0
