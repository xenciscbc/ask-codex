#!/usr/bin/env bash
# ask-codex consultation stopper.
#
#   bash stop.sh '<run directory>' --interval <minutes> --interval-source default|override \
#       --recommended wait|stop [--done '<slugs or none>' --still-running '<slugs>']
#
# Reads `<run directory>/pid` (written by run.sh), ends the whole process tree it names
# (Windows: taskkill /T /F on the Windows pid; elsewhere: the process group created by
# setsid), then verifies that no process of the tree survives and that `events.jsonl` does
# not change during a 5-second observation window. Prints exactly one report line on stdout,
# beginning with `Consultation stopped:`, for the model to copy verbatim; exits 0 only when
# the tree is confirmed ended. Never deletes the run directory. Needs only bash and the
# platform's own tools (Windows: tasklist, taskkill, powershell; Linux/macOS: ps, kill).
set -u

WINDOW_S=5

usage() {
  echo "usage: stop.sh <run directory> --interval <minutes> --interval-source default|override --recommended wait|stop [--done <text> --still-running <text>]" >&2
  exit 2
}
[ $# -ge 1 ] || usage
run_dir="$1"; shift
interval=""; source=""; recommended=""; done_text=""; running_text=""; parallel=0
while [ $# -gt 0 ]; do
  case "$1" in
    --interval) interval="${2:-}"; shift 2 ;;
    --interval-source) source="${2:-}"; shift 2 ;;
    --recommended) recommended="${2:-}"; shift 2 ;;
    --done) done_text="${2:-}"; parallel=1; shift 2 ;;
    --still-running) running_text="${2:-}"; parallel=1; shift 2 ;;
    *) echo "stop.sh: unknown argument: $1" >&2; usage ;;
  esac
done
[ -n "$interval" ] && [ -n "$source" ] && [ -n "$recommended" ] || usage
case "$source" in default|override) ;; *) usage ;; esac
case "$recommended" in wait|stop) ;; *) usage ;; esac
[ -d "$run_dir" ] || { echo "stop.sh: run directory not found: $run_dir" >&2; exit 2; }

# ---- helpers ---------------------------------------------------------------------------

mmss() { printf '%d:%02d' $(( $1 / 60 )) $(( $1 % 60 )); }

mtime() {
  stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0
}

join() { local IFS=", "; echo "$*"; }

# Windows: the pid and all its descendants, via the parent links PowerShell reports.
win_tree() {
  local root="$1" pairs
  pairs="$(powershell.exe -NoProfile -NonInteractive -Command \
    'Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId) $($_.ParentProcessId)" }' 2>/dev/null | tr -d '\r')"
  printf '%s\n' "$pairs" | awk -v root="$root" '
    { child[$1] = $2 }
    END {
      seen[root] = 1; changed = 1
      while (changed) { changed = 0; for (c in child) if (!(c in seen) && (child[c] in seen)) { seen[c] = 1; changed = 1 } }
      for (p in seen) print p
    }'
}

# Windows: is the pid alive? `ps -W` omits some processes (a bash that has exec'd, for
# one), so ask tasklist; its "no tasks" notice is localized, but a match has the pid in
# column 2 whatever the language.
win_alive() {
  tasklist //NH //FI "PID eq $1" 2>/dev/null | awk -v p="$1" '$2 == p { found = 1 } END { exit found ? 0 : 1 }'
}

# POSIX: members of the process group (setsid made the pid its own group id), plus
# descendants by parent pid in case the group was not created.
posix_tree() {
  local root="$1"
  { ps -o pid= -g "$root" 2>/dev/null; echo "$root"; posix_descendants "$root"; } | tr -d ' ' | awk 'NF && !seen[$1]++'
}
posix_descendants() {
  local p c
  for c in $(ps -o pid= --ppid "$1" 2>/dev/null); do echo "$c"; posix_descendants "$c"; done
}
posix_alive() { kill -0 "$1" 2>/dev/null; }

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
  local verdict="$1"
  local line="Consultation stopped: interval $interval minutes ($source); elapsed $elapsed; $last_event; offered: wait another $interval minutes / stop (recommended: $recommended); $verdict"
  if [ "$parallel" = 1 ]; then
    line="$line; done — ${done_text:-none}; still running — ${running_text:-none}"
  fi
  echo "$line"
}

if [ -z "$pid" ] || [ -z "$platform" ]; then
  echo "stop.sh: no usable pid file in $run_dir" >&2
  report "process tree NOT confirmed — pids none recorded"
  exit 2
fi

# ---- kill the tree ---------------------------------------------------------------------

if [ "$platform" = windows ]; then
  if ! win_alive "$pid"; then
    echo "stop.sh: pid $pid is not running" >&2
    report "process tree NOT confirmed — pids $pid (not running)"
    exit 3
  fi
  members="$(win_tree "$pid")"
  [ -n "$members" ] || members="$pid"
  taskkill //T //F //PID "$pid" >/dev/null 2>&1
  sleep 1
  survivors=()
  for p in $members; do win_alive "$p" && survivors+=("$p"); done
  if [ ${#survivors[@]} -gt 0 ]; then
    for p in "${survivors[@]}"; do taskkill //F //PID "$p" >/dev/null 2>&1; done
    sleep 1
    remaining=()
    for p in "${survivors[@]}"; do win_alive "$p" && remaining+=("$p"); done
    survivors=("${remaining[@]+"${remaining[@]}"}")
  fi
else
  if ! posix_alive "$pid"; then
    echo "stop.sh: pid $pid is not running" >&2
    report "process tree NOT confirmed — pids $pid (not running)"
    exit 3
  fi
  members="$(posix_tree "$pid")"
  kill -TERM -- "-$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null
  for p in $members; do kill -TERM "$p" 2>/dev/null; done
  for _ in 1 2 3 4 5 6; do
    alive=0; for p in $members; do posix_alive "$p" && alive=1; done
    [ "$alive" = 0 ] && break
    sleep 0.5
  done
  kill -KILL -- "-$pid" 2>/dev/null
  for p in $members; do kill -KILL "$p" 2>/dev/null; done
  sleep 0.5
  survivors=()
  for p in $members; do posix_alive "$p" && survivors+=("$p"); done
fi

# ---- observation window: events.jsonl must stay still ------------------------------------

before="$(mtime "$events")"
sleep "$WINDOW_S"
after="$(mtime "$events")"
still_writing=0
[ "$before" != "$after" ] && still_writing=1

if [ ${#survivors[@]} -gt 0 ]; then
  echo "stop.sh: processes still alive after taskkill/kill: ${survivors[*]}" >&2
  report "process tree NOT confirmed — pids $(join "${survivors[@]}")"
  exit 1
fi
if [ "$still_writing" = 1 ]; then
  echo "stop.sh: events.jsonl changed during the ${WINDOW_S}s observation window" >&2
  report "process tree NOT confirmed — pids $pid (events.jsonl still changing)"
  exit 1
fi
report "process tree ended"
exit 0
