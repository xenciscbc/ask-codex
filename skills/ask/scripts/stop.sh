#!/usr/bin/env bash
# ask-codex consultation stopper.
#
#   bash stop.sh '<run directory>' --interval <minutes> --interval-source default|override \
#       --recommended wait|stop [--done '<slugs or none>' --still-running '<slugs>']
#
# Reads `<run directory>/pid` (written by run.sh) and ends the whole process tree two ways at
# once: it asks run.sh to do it from inside the child's process namespace (by creating
# `<run directory>/stop-request` and waiting for `stop-result`), and, when the recorded pid is
# visible from here, it also kills the tree directly (Windows: taskkill /T /F on the Windows
# pid; elsewhere: the process group created by setsid). The tree counts as ended when run.sh
# reports `ended`, or when the pid was visible and nothing of its tree survives. It then
# verifies that `events.jsonl` does not change during a 5-second observation window. Prints
# exactly one report line on stdout, beginning with `Consultation stopped:`, for the model to
# copy verbatim; exits 0 only when the tree is confirmed ended. Never deletes the run
# directory. Needs only bash and the platform's own tools.
set -u

WINDOW_S=5
RESULT_WAIT_S=10

usage() {
  echo "usage: stop.sh <run directory> --interval <minutes> --interval-source default|override --recommended wait|stop [--done <text> --still-running <text>]" >&2
  exit 2
}
[ $# -ge 1 ] || usage
run_dir="$1"; shift
interval=""; source=""; recommended=""; done_text=""; running_text=""; parallel=0
while [ $# -gt 0 ]; do
  case "$1" in
    --interval) [ $# -ge 2 ] || usage; interval="$2"; shift 2 ;;
    --interval-source) [ $# -ge 2 ] || usage; source="$2"; shift 2 ;;
    --recommended) [ $# -ge 2 ] || usage; recommended="$2"; shift 2 ;;
    --done) [ $# -ge 2 ] || usage; done_text="$2"; parallel=1; shift 2 ;;
    --still-running) [ $# -ge 2 ] || usage; running_text="$2"; parallel=1; shift 2 ;;
    *) echo "stop.sh: unknown argument: $1" >&2; usage ;;
  esac
done
[ -n "$interval" ] && [ -n "$source" ] && [ -n "$recommended" ] || usage
case "$source" in default|override) ;; *) usage ;; esac
case "$recommended" in wait|stop) ;; *) usage ;; esac
[ -d "$run_dir" ] || { echo "stop.sh: run directory not found: $run_dir" >&2; exit 2; }

# shellcheck source=_tree.sh
. "$(dirname "${BASH_SOURCE[0]}")/_tree.sh"

mmss() { printf '%d:%02d' $(( $1 / 60 )) $(( $1 % 60 )); }
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }

# ---- read the pid file -----------------------------------------------------------------

pid=""; platform=""; started=""
if [ -f "$run_dir/pid" ]; then
  while IFS='=' read -r k v; do
    case "$k" in pid) pid="$v" ;; platform) platform="$v" ;; started) started="$v" ;; esac
  done < "$run_dir/pid"
fi
now="$(date +%s)"
[ -n "$started" ] || started="$(mtime "$run_dir/pid")"
[ "$started" -gt 0 ] 2>/dev/null || started="$now"
elapsed="$(mmss $(( now - started )))"

events="$run_dir/events.jsonl"
if [ -s "$events" ]; then
  type="$(tail -n 1 "$events" | sed -n 's/.*"type"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
  [ -n "$type" ] || type="unknown"
  last_event="last event $type $(mmss $(( now - $(mtime "$events") ))) ago"
else
  last_event="no events"
fi

report() {
  local line="Consultation stopped: interval $interval minutes ($source); elapsed $elapsed; $last_event; offered: wait another $interval minutes / stop (recommended: $recommended); $1"
  [ "$parallel" = 1 ] && line="$line; done — ${done_text:-none}; still running — ${running_text:-none}"
  echo "$line"
  # The model copies the line at the moment of the stop; say so where it is looking — and say
  # nothing else here (a procedural hint in this output was followed over the skill's own order).
  echo "stop.sh: copy the line above, verbatim, as the first line of your next message, before anything else." >&2
  # The lines the final answer must open with, shown again by the cleanup command
  # (`cat -- '<run dir>/stop-report'; rm -rf -- '<run dir>'`) right before that answer is written.
  {
    echo "Begin your final answer with these lines, verbatim (markdown emphasis around the fixed words is allowed):"
    echo "$line"
    [ "$parallel" = 1 ] && echo "Parallel check: done — ${done_text:-none}; still running — ${running_text:-none}."
  } > "$run_dir/stop-report"
}

if [ -z "$pid" ] || [ -z "$platform" ]; then
  echo "stop.sh: no usable pid file in $run_dir" >&2
  report "process tree NOT confirmed — pids none recorded"
  exit 2
fi

# ---- stop the tree: cooperative request plus direct kill when the pid is visible ---------

rm -f "$run_dir/stop-result"
: > "$run_dir/stop-request"

ended=0; survivors=""
if [ -e "$run_dir/exit-code" ]; then
  # The launched command already ended by itself; its pid may be gone or reused by an unrelated
  # process. Do not kill anything and do not wait for stop-result — the tree already ended.
  ended_code="$(cat -- "$run_dir/exit-code" 2>/dev/null)"
  echo "stop.sh: the command had already ended by itself with exit status ${ended_code}; nothing was killed" >&2
  ended=1
else
  visible=0; direct_survivors=""
  if tree_alive "$platform" "$pid"; then
    visible=1
    direct_survivors="$(tree_kill "$platform" "$pid")"
  fi

  result=""
  for _ in $(seq 1 $(( RESULT_WAIT_S * 2 ))); do
    [ -s "$run_dir/stop-result" ] && { result="$(cat "$run_dir/stop-result")"; break; }
    # Nothing to wait for once the pid was visible and its tree is gone.
    [ "$visible" = 1 ] && [ -z "$direct_survivors" ] && ! tree_alive "$platform" "$pid" && break
    sleep 0.5
  done

  case "$result" in
    ended) ended=1 ;;
    survivors\ *) survivors="${result#survivors }" ;;
  esac
  if [ "$ended" = 0 ] && [ -z "$survivors" ] && [ "$visible" = 1 ]; then
    if [ -n "$direct_survivors" ]; then survivors="$direct_survivors"
    elif ! tree_alive "$platform" "$pid"; then ended=1
    else survivors="$pid"
    fi
  fi
fi

# ---- observation window: events.jsonl must stay still ------------------------------------

before="$(mtime "$events")"
sleep "$WINDOW_S"
after="$(mtime "$events")"

if [ "$ended" = 0 ]; then
  if [ -n "$survivors" ]; then
    echo "stop.sh: processes still alive after the kill: $survivors" >&2
    report "process tree NOT confirmed — pids $survivors"
  else
    echo "stop.sh: pid $pid is not visible from here and run.sh gave no answer within ${RESULT_WAIT_S}s" >&2
    report "process tree NOT confirmed — pids $pid (not running)"
    exit 3
  fi
  exit 1
fi
if [ "$before" != "$after" ]; then
  echo "stop.sh: events.jsonl changed during the ${WINDOW_S}s observation window" >&2
  report "process tree NOT confirmed — pids $pid (events.jsonl still changing)"
  exit 1
fi
report "process tree ended"
exit 0
