#!/usr/bin/env bash
# ask-codex consultation launcher.
#
#   bash run.sh '<run directory>' -- codex exec … - < prompt.md > events.jsonl 2> stderr.log
#
# Prefix for the skill's `codex exec` command: the command and its redirections stay on the
# caller's line, untouched. The script starts the command as a child that owns its own
# process tree (Linux/macOS: its own session via setsid; Windows Git Bash: the child's
# Windows pid is recorded), writes `<run directory>/pid` for stop.sh, then waits and exits
# with the command's exit code.
#
# Cooperative stop: while it waits, the script watches for `<run directory>/stop-request`
# (created by stop.sh). When it appears, the script — which shares the child's process
# namespace even where stop.sh cannot see the pid, as in a sandbox that gives every command
# its own PID namespace — kills the whole tree, verifies it, and writes the outcome to
# `<run directory>/stop-result` (`ended`, or `survivors <pids>`). Needs only bash and the
# platform's own tools.
set -u

usage() { echo "usage: run.sh <run directory> -- <command…>" >&2; exit 2; }
[ $# -ge 3 ] || usage
run_dir="$1"; shift
[ "$1" = "--" ] || usage
shift
[ -d "$run_dir" ] || { echo "run.sh: run directory not found: $run_dir" >&2; exit 2; }

# shellcheck source=_tree.sh
. "$(dirname "${BASH_SOURCE[0]}")/_tree.sh"

started="$(date +%s)"
platform="$(tree_platform)"
rm -f "$run_dir/stop-request" "$run_dir/stop-result"

# A background job (`&`) of a non-interactive shell gets /dev/null as stdin unless stdin is
# redirected explicitly, and the prompt arrives on stdin (`- < prompt.md`): keep it.
exec 3<&0
if [ "$platform" = posix ] && command -v setsid >/dev/null 2>&1; then
  # A background job of a non-interactive shell is not a group leader, so setsid does not
  # fork: the recorded pid is the command's own, and it is also the new group/session id.
  setsid "$@" <&3 &
else
  "$@" <&3 &
fi
child=$!
exec 3<&-

root="$child"
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
  root="$winpid"
  extra="msys_pid=$child"
fi

{
  echo "pid=$root"
  echo "platform=$platform"
  echo "started=$started"
  [ -n "$extra" ] && echo "$extra"
} > "$run_dir/pid"

# Watcher: on a stop request, kill the tree from inside this process namespace.
(
  while sleep 0.5; do
    [ -e "$run_dir/stop-request" ] || continue
    [ -n "$root" ] && tree_kill "$platform" "$root" >/dev/null
    exit 0
  done
) &
watcher=$!

wait "$child"
status=$?
kill "$watcher" 2>/dev/null

if [ -e "$run_dir/stop-request" ]; then
  survivors=""
  if [ -n "$root" ]; then
    # The child is gone (wait returned); make sure nothing of its tree is left.
    for p in $(tree_members "$platform" "$root"); do
      tree_alive "$platform" "$p" && survivors="${survivors:+$survivors, }$p"
    done
  fi
  if [ -z "$survivors" ]; then echo "ended" > "$run_dir/stop-result"; else echo "survivors $survivors" > "$run_dir/stop-result"; fi
fi
exit $status
