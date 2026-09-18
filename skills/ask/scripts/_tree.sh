# Shared process-tree helpers for run.sh and stop.sh (sourced, not executed).
# Needs only bash and the platform's own tools: Windows Git Bash — ps, tasklist, taskkill,
# powershell.exe; Linux/macOS — ps, kill, setsid.

tree_platform() {
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) echo windows ;;
    *) echo posix ;;
  esac
}

# Windows: is the pid alive? `ps -W` omits some processes (a bash that has exec'd, for one),
# so ask tasklist; its "no tasks" notice is localized, but a match has the pid in column 2.
win_alive() {
  tasklist //NH //FI "PID eq $1" 2>/dev/null | awk -v p="$1" '$2 == p { found = 1 } END { exit found ? 0 : 1 }'
}

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

posix_alive() { kill -0 "$1" 2>/dev/null; }

posix_descendants() {
  local c
  for c in $(ps -o pid= --ppid "$1" 2>/dev/null); do echo "$c"; posix_descendants "$c"; done
}

# POSIX: the process group (setsid made the root its own group id), the root, and its
# descendants by parent pid in case the group was not created.
posix_tree() {
  local root="$1"
  { ps -o pid= -g "$root" 2>/dev/null; echo "$root"; posix_descendants "$root"; } | tr -d ' ' | awk 'NF && !seen[$1]++'
}

tree_alive() {
  if [ "$1" = windows ]; then win_alive "$2"; else posix_alive "$2"; fi
}

tree_members() {
  local m
  if [ "$1" = windows ]; then m="$(win_tree "$2")"; else m="$(posix_tree "$2")"; fi
  [ -n "$m" ] || m="$2"
  echo "$m"
}

# Kill the whole tree rooted at $2 and print the pids that survived (empty on success).
tree_kill() {
  local platform="$1" root="$2" members p alive survivors=()
  members="$(tree_members "$platform" "$root")"
  if [ "$platform" = windows ]; then
    taskkill //T //F //PID "$root" >/dev/null 2>&1
    sleep 1
    for p in $members; do win_alive "$p" && survivors+=("$p"); done
    if [ ${#survivors[@]} -gt 0 ]; then
      for p in "${survivors[@]}"; do taskkill //F //PID "$p" >/dev/null 2>&1; done
      sleep 1
      local remaining=()
      for p in "${survivors[@]}"; do win_alive "$p" && remaining+=("$p"); done
      survivors=("${remaining[@]+"${remaining[@]}"}")
    fi
  else
    kill -TERM -- "-$root" 2>/dev/null; kill -TERM "$root" 2>/dev/null
    for p in $members; do kill -TERM "$p" 2>/dev/null; done
    for _ in 1 2 3 4 5 6; do
      alive=0; for p in $members; do posix_alive "$p" && alive=1; done
      [ "$alive" = 0 ] && break
      sleep 0.5
    done
    kill -KILL -- "-$root" 2>/dev/null
    for p in $members; do kill -KILL "$p" 2>/dev/null; done
    sleep 0.5
    for p in $members; do posix_alive "$p" && survivors+=("$p"); done
  fi
  [ ${#survivors[@]} -gt 0 ] && { local IFS=", "; echo "${survivors[*]}"; }
  return 0
}
