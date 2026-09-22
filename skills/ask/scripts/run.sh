#!/usr/bin/env bash
# Launch one consultation and own its process identity and cooperative stop lifecycle.
set -u

if [ -x /usr/bin/uname ] && case "$(/usr/bin/uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) true ;; *) false ;; esac; then
  PATH="/usr/bin:/bin:$PATH"; export PATH
fi

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
identities="$run_dir/process-identities"
# A pre-existing stop-request is an early cancellation created after the launcher process was
# spawned but before initialization reached this point. Unique run directories make it safe and
# necessary to preserve it.
rm -f "$run_dir/stop-result" "$run_dir/stop-status.json" \
  "$run_dir/watcher-finish" "$run_dir/exit-code" "$run_dir/launcher-result.json" \
  "$identities" "$identities.complete" "$identities.verified" "$identities.unverified-reason"
rm -f "$identities.owned"

exec 3<&0
if command -v setsid >/dev/null 2>&1; then
  setsid "$@" <&3 &
else
  "$@" <&3 &
fi
child=$!
exec 3<&-

root="$child"; extra=""
if [ "$platform" = windows ]; then
  winpid=""
  for _ in 1 2 3 4 5; do
    winpid="$(ps 2>/dev/null | awk -v p="$child" '$1 == p { print $4; exit }')"
    [ -n "$winpid" ] && break
    sleep 0.2
  done
  root="$winpid"; extra="msys_pid=$child"
fi

root_identity=""
if [ -n "$root" ]; then
  for _ in 1 2 3 4 5; do
    root_identity="$(tree_identity "$platform" "$root")"
    [ -n "$root_identity" ] && break
    sleep 0.1
  done
fi
{
  echo "pid=$root"
  echo "platform=$platform"
  echo "started=$started"
  echo "identity=$root_identity"
  [ -n "$extra" ] && echo "$extra"
} > "$run_dir/pid"
[ -n "$root_identity" ] && printf '%s|%s\n' "$root" "$root_identity" > "$identities"
[ "$platform" = posix ] && [ -n "$root_identity" ] && : > "$identities.owned"
tree_capture "$platform" "$root" "$identities" >/dev/null 2>&1 || true

(
  while :; do
    tree_capture "$platform" "$root" "$identities" >/dev/null 2>&1 || true
    if [ -e "$run_dir/stop-request" ]; then
      # Git Bash can terminate the MSYS process group even when Windows management APIs are
      # unavailable to a sandboxed caller. setsid above makes child the group leader.
      if [ "$platform" = windows ] && tree_identity_matches "$platform" "$root" "$root_identity"; then
        kill -TERM -- "-$child" 2>/dev/null || true
        kill -TERM "$child" 2>/dev/null || true
        sleep 0.1
        tree_identity_matches "$platform" "$root" "$root_identity" && kill -KILL "$child" 2>/dev/null || true
      fi
      survivors="$(tree_kill "$platform" "$root" "$identities")"
      [ "$platform" = windows ] && survivors="$(tree_all_survivors "$platform" "$root" "$identities")"
      if [ -z "$survivors" ] && [ -s "$identities" ] && tree_verification_complete "$platform" "$identities"; then
        result="ended"
      elif [ -n "$survivors" ]; then
        result="survivors $survivors"
      else
        result="unconfirmed identity or complete tree enumeration unavailable"
      fi
      printf '%s\n' "$result" > "$run_dir/stop-result.tmp" && mv -f "$run_dir/stop-result.tmp" "$run_dir/stop-result"
      exit 0
    fi
    [ -e "$run_dir/watcher-finish" ] && exit 0
    sleep 0.25
  done
) </dev/null >/dev/null 2>&1 &
watcher=$!

wait "$child"
status=$?
printf '%s\n' "$status" > "$run_dir/exit-code.tmp" && mv -f "$run_dir/exit-code.tmp" "$run_dir/exit-code"

if [ -e "$run_dir/stop-request" ]; then
  # Do not cancel termination/verification merely because the root exited promptly.
  wait "$watcher" 2>/dev/null || true
else
  # Let an in-flight identity capture finish so none of its platform helpers are orphaned.
  : > "$run_dir/watcher-finish"
  wait "$watcher" 2>/dev/null || true
  rm -f "$run_dir/watcher-finish"
  # A consultation root must not leave helpers behind on otherwise normal completion.
  normal_survivors="$(tree_all_survivors "$platform" "$root" "$identities")"
  if [ -n "$normal_survivors" ]; then
    cleanup_survivors="$(tree_kill "$platform" "$root" "$identities")"
    if [ -n "$cleanup_survivors" ] || ! tree_verification_complete "$platform" "$identities"; then
      : > "$run_dir/stop-request"
      if [ -n "$cleanup_survivors" ]; then
        printf 'survivors %s\n' "$cleanup_survivors" > "$run_dir/stop-result"
      else
        printf 'unconfirmed normal-completion descendant cleanup\n' > "$run_dir/stop-result"
      fi
    fi
  fi
fi
rm -f "$identities.owned"
printf '{"exit_code":%s}\n' "$status" > "$run_dir/launcher-result.json.tmp" && \
  mv -f "$run_dir/launcher-result.json.tmp" "$run_dir/launcher-result.json"
exit "$status"
