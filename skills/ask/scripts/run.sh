#!/usr/bin/env bash
# ask-codex consultation launcher.
#
#   bash run.sh '<run directory>' -- codex exec … - < prompt.md > events.jsonl 2> stderr.log
#
# Prefix for the skill's `codex exec` command: the command and its redirections stay on the
# caller's line, untouched. The script starts the command as a child that owns its own
# process tree (Linux/macOS: its own session via setsid; Windows Git Bash: the child's
# Windows pid is recorded), writes `<run directory>/pid` for stop.sh, then waits and exits
# with the command's exit code. Needs only bash and the platform's own tools.
set -u

usage() { echo "usage: run.sh <run directory> -- <command…>" >&2; exit 2; }
[ $# -ge 3 ] || usage
run_dir="$1"; shift
[ "$1" = "--" ] || usage
shift
[ -d "$run_dir" ] || { echo "run.sh: run directory not found: $run_dir" >&2; exit 2; }

started="$(date +%s)"
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) platform=windows ;;
  *) platform=posix ;;
esac

if [ "$platform" = posix ] && command -v setsid >/dev/null 2>&1; then
  # A background job of a non-interactive shell is not a group leader, so setsid does not
  # fork: the recorded pid is the command's own, and it is also the new group/session id.
  setsid "$@" &
else
  "$@" &
fi
child=$!

pid="$child"
extra=""
if [ "$platform" = windows ]; then
  # `ps` (MSYS) lists the shell's own children with their Windows pid in the WINPID column;
  # taskkill needs the Windows pid.
  winpid=""
  for _ in 1 2 3 4 5; do
    winpid="$(ps 2>/dev/null | awk -v p="$child" '$1 == p { print $4; exit }')"
    [ -n "$winpid" ] && break
    sleep 0.2
  done
  pid="$winpid"
  extra="msys_pid=$child"
fi

{
  echo "pid=$pid"
  echo "platform=$platform"
  echo "started=$started"
  [ -n "$extra" ] && echo "$extra"
} > "$run_dir/pid"

wait "$child"
exit $?
