# Shared process-tree helpers for run.sh and stop.sh (sourced, not executed).
# Every destructive operation is bound to a captured process identity. A numeric pid alone is
# never enough: it may have been reused by an unrelated process.

# Git Bash can be launched directly by a host whose sanitized PATH omits Git's own tools.
if [ -x /usr/bin/uname ] && case "$(/usr/bin/uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) true ;; *) false ;; esac; then
  PATH="/usr/bin:/bin:$PATH"; export PATH
fi

tree_platform() {
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) echo windows ;;
    *) echo posix ;;
  esac
}

win_alive() {
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
  tasklist //NH //FI "PID eq $1" 2>/dev/null | awk -v p="$1" '$2 == p { found = 1 } END { exit found ? 0 : 1 }'
}

win_identity() {
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
  powershell.exe -NoProfile -NonInteractive -Command \
    "\$p=Get-Process -Id $1 -ErrorAction SilentlyContinue; if (\$p) { \$p.StartTime.ToUniversalTime().Ticks }" \
    2>/dev/null | tr -d '\r\n'
}

win_tree() {
  local root="$1" pairs
  case "$root" in ''|*[!0-9]*) return 1 ;; esac
  pairs="$(powershell.exe -NoProfile -NonInteractive -Command \
    'try { $items = @(Get-CimInstance Win32_Process -ErrorAction Stop); "__TREE_OK__"; $items | ForEach-Object { "$($_.ProcessId) $($_.ParentProcessId)" } } catch { $items = @(Get-Process -ErrorAction Stop); if ($items.Count -eq 0 -or -not ($items[0].PSObject.Properties.Name -contains "Parent")) { exit 1 }; "__TREE_OK__"; $items | ForEach-Object { try { $parent = $_.Parent; if ($parent) { "$($_.Id) $($parent.Id)" } } catch {} } }' \
    2>/dev/null | tr -d '\r')"
  printf '%s\n' "$pairs" | awk -v root="$root" '
    $0 == "__TREE_OK__" { ok = 1; next }
    { parent[$1] = $2 }
    END {
      if (!ok) exit 1
      print "__TREE_OK__"
      seen[root] = 1; changed = 1
      while (changed) { changed = 0; for (c in parent) if (!(c in seen) && (parent[c] in seen)) { seen[c] = 1; changed = 1 } }
      for (p in seen) print p
    }'
}

posix_alive() {
  local state
  state="$(ps -o stat= -p "$1" 2>/dev/null | awk 'NR == 1 { print substr($1,1,1) }')"
  [ -n "$state" ] && [ "$state" != Z ]
}

posix_proc_starttime() {
  local stat rest start
  stat="$(cat "$1" 2>/dev/null)" || return 1
  case "$stat" in
    *')'*) rest="${stat##*)}" ;;
    *) return 1 ;;
  esac
  # The comm field may contain spaces, parentheses, and newlines. Its delimiter is the
  # final ')' in the record; everything after it starts with whitespace and field 3.
  case "$rest" in [[:space:]]*) ;; *) return 1 ;; esac
  start="$(printf '%s\n' "$rest" | awk '
    { for (i = 1; i <= NF; i++) field[++count] = $i }
    END {
      if (count < 20 || field[20] !~ /^[0-9]+$/) exit 1
      print field[20]
    }')" || return 1
  [ -n "$start" ] || return 1
  printf '%s\n' "$start"
}

posix_identity() {
  local stat_file="/proc/$1/stat" start
  if [ -r "$stat_file" ]; then
    start="$(posix_proc_starttime "$stat_file")" || return 1
    printf 'proc:%s\n' "$start"
    return
  fi
  ps -o lstart= -p "$1" 2>/dev/null | awk 'NR == 1 { gsub(/[[:space:]]+/, "_"); print }'
}

posix_group_owned() {
  local root="$1" identities="$2" expected actual
  expected="$(awk -F'|' -v p="$root" '$1 == p { print $2; exit }' "$identities" 2>/dev/null)"
  [ -n "$expected" ] || return 1
  actual="$(posix_identity "$root")"
  if [ -n "$actual" ]; then
    [ "$actual" = "$expected" ]
  else
    # A group can outlive its leader; a live replacement must never inherit ownership.
    ! posix_alive "$root"
  fi
}

posix_tree() {
  local root="$1" identities="${2:-}" rows seeds="" pid expected root_group=""
  if [ -n "$identities" ] && [ -f "$identities" ]; then
    while IFS='|' read -r pid expected; do
      [ -n "$pid" ] && [ -n "$expected" ] || continue
      tree_identity_matches posix "$pid" "$expected" && seeds="$seeds,$pid"
    done < "$identities"
  fi
  # A numeric root is only a process-group key, never an unverified PPID seed: after
  # root exit its PID may belong to an unrelated parent outside the original group.
  # One successful global snapshot supplies both PPID ancestry and process-group membership.
  # Seeding captured identity-matching members keeps following a detached/reparented subtree
  # after it leaves the original setsid group.
  rows="$(ps -axo pid=,ppid=,pgid= 2>/dev/null)" || return 1
  posix_group_owned "$root" "$identities" && root_group="$root"
  printf '%s\n' "__TREE_OK__"
  printf '%s\n' "$rows" | awk -v seeds="$seeds" -v root_group="$root_group" '
    BEGIN { n = split(seeds, s, ","); for (i = 1; i <= n; i++) if (s[i] != "") seen[s[i]] = 1 }
    { parent[$1] = $2; group[$1] = $3; if ($3 == root_group) seen[$1] = 1 }
    END {
      changed = 1
      while (changed) {
        changed = 0
        for (p in parent) {
          if (!(p in seen) && ((parent[p] in seen) || (group[p] in seen))) {
            seen[p] = 1; changed = 1
          }
        }
      }
      for (p in parent) if (p in seen) print p
    }'
}

tree_alive() {
  case "$2" in ''|*[!0-9]*) return 1 ;; esac
  if [ "$1" = windows ]; then win_alive "$2"; else posix_alive "$2"; fi
}

tree_identity() {
  case "$2" in ''|*[!0-9]*) return 1 ;; esac
  if [ "$1" = windows ]; then win_identity "$2"; else posix_identity "$2"; fi
}

tree_members() {
  case "$2" in ''|*[!0-9]*) return 1 ;; esac
  if [ "$1" = windows ]; then win_tree "$2"; else posix_tree "$2" "${3:-}"; fi
}

tree_capture() {
  local platform="$1" root="$2" identities="$3" p identity listing complete=1
  [ -n "$root" ] || return 1
  touch "$identities"
  if [ "$platform" = posix ]; then
    listing="$(posix_tree "$root" "$identities")"
  else
    listing="$(tree_members "$platform" "$root")"
  fi
  printf '%s\n' "$listing" | grep -q '^__TREE_OK__$' || { rm -f "$identities.complete"; return 1; }
  listing="$(printf '%s\n' "$listing" | sed '/^__TREE_OK__$/d')"
  for p in $listing; do
    case "$p" in ''|*[!0-9]*) continue ;; esac
    grep -q "^${p}|" "$identities" 2>/dev/null && continue
    identity="$(tree_identity "$platform" "$p")"
    if [ -n "$identity" ]; then
      printf '%s|%s\n' "$p" "$identity" >> "$identities"
    elif tree_alive "$platform" "$p"; then
      complete=0
    fi
  done
  if [ "$complete" = 1 ]; then : > "$identities.complete"; else rm -f "$identities.complete"; fi
}

tree_verification_complete() { [ -f "$2.verified" ]; }

tree_identity_matches() {
  local platform="$1" pid="$2" expected="$3" actual
  actual="$(tree_identity "$platform" "$pid")"
  [ -n "$actual" ] && [ "$actual" = "$expected" ]
}

tree_survivors() {
  local platform="$1" identities="$2" pid expected survivors=""
  [ -f "$identities" ] || return 0
  while IFS='|' read -r pid expected; do
    [ -n "$pid" ] && [ -n "$expected" ] || continue
    if tree_alive "$platform" "$pid" && tree_identity_matches "$platform" "$pid" "$expected"; then
      survivors="${survivors:+$survivors, }$pid"
    fi
  done < "$identities"
  [ -n "$survivors" ] && printf '%s\n' "$survivors"
}

tree_all_survivors() {
  local platform="$1" root="$2" identities="$3" survivors p current
  survivors="$(tree_survivors "$platform" "$identities")"
  if [ "$platform" = posix ]; then
    current="$(tree_members "$platform" "$root" "$identities" 2>/dev/null | sed '/^__TREE_OK__$/d')"
    for p in $current; do
      tree_alive "$platform" "$p" || continue
      case ", $survivors, " in *", $p, "*) ;; *) survivors="${survivors:+$survivors, }$p" ;; esac
    done
  fi
  [ -n "$survivors" ] && printf '%s\n' "$survivors"
}

tree_kill() {
  local platform="$1" root="$2" identities="$3" root_expected pid expected survivors owned=0 current
  rm -f "$identities.verified" "$identities.unverified-reason"
  root_expected="$(awk -F'|' -v p="$root" '$1 == p { print $2; exit }' "$identities" 2>/dev/null)"
  [ -n "$root_expected" ] || {
    printf 'root_identity_unmatched\n' > "$identities.unverified-reason"
    tree_survivors "$platform" "$identities"; return 0;
  }
  if tree_identity_matches "$platform" "$root" "$root_expected"; then
    owned=1
    tree_capture "$platform" "$root" "$identities" >/dev/null 2>&1 || true
    [ "$platform" = windows ] && taskkill //T //F //PID "$root" >/dev/null 2>&1
  elif ! tree_alive "$platform" "$root"; then
    # A dead recorded root can still own a live setsid group. Require either a matching captured
    # member in that group or a complete prior scan showing that the group is already empty.
    if [ "$platform" = posix ]; then
      [ -f "$identities.owned" ] && owned=1
      current="$(tree_members "$platform" "$root" "$identities" 2>/dev/null | sed '/^__TREE_OK__$/d')"
      for p in $current; do
        expected="$(awk -F'|' -v n="$p" '$1 == n { print $2; exit }' "$identities")"
        [ -n "$expected" ] && tree_identity_matches "$platform" "$p" "$expected" && owned=1
      done
      [ -z "$current" ] && [ -f "$identities.complete" ] && owned=1
    elif [ -f "$identities.complete" ]; then
      owned=1
    fi
  fi
  [ "$owned" = 1 ] || {
    printf 'root_identity_unmatched\n' > "$identities.unverified-reason"
    tree_survivors "$platform" "$identities"; return 0;
  }

  if [ "$platform" = posix ] && posix_group_owned "$root" "$identities"; then
    kill -TERM -- "-$root" 2>/dev/null
  fi

  while IFS='|' read -r pid expected; do
    [ -n "$pid" ] && tree_identity_matches "$platform" "$pid" "$expected" || continue
    if [ "$platform" = windows ]; then taskkill //F //PID "$pid" >/dev/null 2>&1
    else kill -TERM "$pid" 2>/dev/null
    fi
  done < <(awk '{ a[NR]=$0 } END { for (i=NR;i>0;i--) print a[i] }' "$identities")

  # Deterministic integration-test seam for the root-exit / verification race.
  [ -n "${ASK_CODEX_TREE_VERIFY_DELAY_S:-}" ] && sleep "$ASK_CODEX_TREE_VERIFY_DELAY_S"

  for _ in 1 2 3 4 5 6; do
    tree_capture "$platform" "$root" "$identities" >/dev/null 2>&1 || true
    survivors="$(tree_all_survivors "$platform" "$root" "$identities")"
    [ -z "$survivors" ] && break
    sleep 0.5
  done
  if [ -n "$survivors" ]; then
    if [ "$platform" = posix ]; then
      tree_capture "$platform" "$root" "$identities" >/dev/null 2>&1 || true
      posix_group_owned "$root" "$identities" && kill -KILL -- "-$root" 2>/dev/null
    fi
    while IFS='|' read -r pid expected; do
      [ -n "$pid" ] && tree_identity_matches "$platform" "$pid" "$expected" || continue
      if [ "$platform" = windows ]; then taskkill //F //PID "$pid" >/dev/null 2>&1
      else kill -KILL "$pid" 2>/dev/null
      fi
    done < <(awk '{ a[NR]=$0 } END { for (i=NR;i>0;i--) print a[i] }' "$identities")
    sleep 0.5
  fi
  tree_capture "$platform" "$root" "$identities" >/dev/null 2>&1 || true
  survivors="$(tree_all_survivors "$platform" "$root" "$identities")"
  [ -z "$survivors" ] && [ -f "$identities.complete" ] && : > "$identities.verified"
  [ -n "$survivors" ] && printf '%s\n' "$survivors"
  return 0
}
