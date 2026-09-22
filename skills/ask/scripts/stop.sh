#!/usr/bin/env bash
# Request and verify termination of one consultation. stop-status.json is the machine-readable
# contract; stdout is only a concise human diagnostic.
set -u

if [ -x /usr/bin/uname ] && case "$(/usr/bin/uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) true ;; *) false ;; esac; then
  PATH="/usr/bin:/bin:$PATH"; export PATH
fi

WINDOW_S="${ASK_CODEX_STOP_WINDOW_S:-5}"
RESULT_WAIT_S="${ASK_CODEX_STOP_RESULT_WAIT_S:-10}"

usage() {
  echo "usage: stop.sh <run directory> --interval <minutes> --interval-source default|override --recommended wait|stop [--offered none|wait,stop] [--done <text> --still-running <text>]" >&2
  exit 2
}
[ $# -ge 1 ] || usage
run_dir="$1"; shift
interval=""; source=""; recommended=""; offered="none"; done_text=""; running_text=""; parallel=0
while [ $# -gt 0 ]; do
  case "$1" in
    --interval) [ $# -ge 2 ] || usage; interval="$2"; shift 2 ;;
    --interval-source) [ $# -ge 2 ] || usage; source="$2"; shift 2 ;;
    --recommended) [ $# -ge 2 ] || usage; recommended="$2"; shift 2 ;;
    --offered) [ $# -ge 2 ] || usage; offered="$2"; shift 2 ;;
    --done) [ $# -ge 2 ] || usage; done_text="$2"; parallel=1; shift 2 ;;
    --still-running) [ $# -ge 2 ] || usage; running_text="$2"; parallel=1; shift 2 ;;
    *) echo "stop.sh: unknown argument: $1" >&2; usage ;;
  esac
done
case "$interval" in ''|*[!0-9]*) usage ;; esac
[ "$interval" -gt 0 ] || usage
case "$source" in default|override) ;; *) usage ;; esac
case "$recommended" in wait|stop) ;; *) usage ;; esac
case "$offered" in none|wait,stop) ;; *) usage ;; esac
[ -d "$run_dir" ] || { echo "stop.sh: run directory not found: $run_dir" >&2; exit 2; }

# shellcheck source=_tree.sh
. "$(dirname "${BASH_SOURCE[0]}")/_tree.sh"

mmss() { printf '%d:%02d' $(( $1 / 60 )) $(( $1 % 60 )); }
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\r/\\r/g; s/\t/\\t/g'; }
json_string() { printf '"%s"' "$(json_escape "$1")"; }

pid=""; platform=""; started=""; recorded_identity=""
if [ -f "$run_dir/pid" ]; then
  while IFS='=' read -r k v; do
    case "$k" in pid) pid="$v" ;; platform) platform="$v" ;; started) started="$v" ;; identity) recorded_identity="$v" ;; esac
  done < "$run_dir/pid"
fi
now="$(date +%s)"
[ -n "$started" ] || started="$(mtime "$run_dir/pid")"
[ "$started" -gt 0 ] 2>/dev/null || started="$now"
elapsed_seconds=$(( now - started )); [ "$elapsed_seconds" -ge 0 ] || elapsed_seconds=0
elapsed="$(mmss "$elapsed_seconds")"

events="$run_dir/events.jsonl"; event_type=""; event_age=""
if [ -s "$events" ]; then
  event_type="$(tail -n 1 "$events" | sed -n 's/.*"type"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
  [ -n "$event_type" ] || event_type="unknown"
  event_age=$(( now - $(mtime "$events") )); [ "$event_age" -ge 0 ] || event_age=0
  last_event="last event $event_type $(mmss "$event_age") ago"
else
  last_event="no events"
fi

write_status() {
  local status="$1" confirmed="$2" evidence="$3" survivors="$4" retained_json="null" event_json="null" parallel_json="null" offered_json="[]"
  [ "$confirmed" = false ] && retained_json="$(json_string "$run_dir")"
  if [ -n "$event_type" ]; then
    event_json="{\"type\":$(json_string "$event_type"),\"age_seconds\":$event_age}"
  fi
  if [ "$parallel" = 1 ]; then
    parallel_json="{\"done\":$(json_string "${done_text:-none}"),\"still_running\":$(json_string "${running_text:-none}")}"
  fi
  [ "$offered" = "wait,stop" ] && offered_json='["wait","stop"]'
  {
    printf '{"schema_version":1,"status":%s,"confirmed":%s,' "$(json_string "$status")" "$confirmed"
    printf '"interval_minutes":%s,"interval_source":%s,"elapsed_seconds":%s,' "$interval" "$(json_string "$source")" "$elapsed_seconds"
    printf '"last_event":%s,"options_offered":%s,"recommended":%s,' "$event_json" "$offered_json" "$(json_string "$recommended")"
    printf '"termination":{"evidence":%s,"recorded_pid":%s,"recorded_identity":%s,"survivors":%s,"exit_code_present":%s},' \
      "$(json_string "$evidence")" "$(json_string "${pid:-}")" "$(json_string "${recorded_identity:-}")" "$(json_string "${survivors:-}")" "$([ -e "$run_dir/exit-code" ] && echo true || echo false)"
    printf '"retained_location":%s,"parallel":%s}\n' "$retained_json" "$parallel_json"
  } > "$run_dir/stop-status.json.tmp" && mv -f "$run_dir/stop-status.json.tmp" "$run_dir/stop-status.json"
}

report() { printf 'stop.sh: %s; status=%s\n' "$1" "$run_dir/stop-status.json"; }

identities="$run_dir/process-identities"
rm -f "$run_dir/stop-report"
if [ -z "$pid" ] || case "$pid" in *[!0-9]*) true ;; *) false ;; esac || \
   case "$platform" in windows|posix) false ;; *) true ;; esac || [ ! -s "$identities" ]; then
  echo "stop.sh: no usable captured process identity in $run_dir" >&2
  : > "$run_dir/stop-request"
  write_status unconfirmed_stop false identity_unavailable "${pid:-none recorded}"
  report "termination unconfirmed"
  exit 2
fi

rm -f "$run_dir/stop-result"
: > "$run_dir/stop-request"
direct_survivors="$(tree_kill "$platform" "$pid" "$identities")"

result=""
for _ in $(seq 1 $(( RESULT_WAIT_S * 2 ))); do
  [ -s "$run_dir/stop-result" ] && { result="$(cat "$run_dir/stop-result")"; break; }
  [ -s "$identities.unverified-reason" ] && [ -e "$run_dir/exit-code" ] && break
  current="$(tree_all_survivors "$platform" "$pid" "$identities")"
  [ -z "$current" ] && tree_verification_complete "$platform" "$identities" && break
  sleep 0.5
done

survivors="$(tree_all_survivors "$platform" "$pid" "$identities")"
confirmed=0; evidence="verification_incomplete"; complete=0; enumerated=0
[ -f "$identities.complete" ] && enumerated=1
tree_verification_complete "$platform" "$identities" && complete=1
case "$result" in
  ended) [ "$complete" = 1 ] && [ -z "$survivors" ] && { confirmed=1; evidence="launcher_identity_verified"; } ;;
  survivors\ *) survivors="${result#survivors }" ;;
  unconfirmed\ *) evidence="${result#unconfirmed }" ;;
esac
if [ "$confirmed" = 0 ] && [ "$complete" = 1 ] && [ -z "$survivors" ]; then
  confirmed=1; evidence="captured_identities_absent"
fi
if [ "$complete" != 1 ]; then
  if [ -s "$identities.unverified-reason" ]; then evidence="$(cat "$identities.unverified-reason")"
  elif [ "$enumerated" = 1 ]; then evidence="tree_ownership_unproven"
  else evidence="tree_enumeration_unavailable"
  fi
fi
[ -n "$survivors" ] || survivors="$direct_survivors"

before="$(mtime "$events")"
sleep "$WINDOW_S"
after="$(mtime "$events")"
if [ "$before" != "$after" ]; then
  confirmed=0; evidence="events_still_changing"
  [ -n "$survivors" ] || survivors="$pid"
fi

if [ "$confirmed" = 1 ]; then
  write_status confirmed_stop true "$evidence" ""
  report "termination confirmed"
  exit 0
fi

[ -n "$survivors" ] || survivors="$pid (verification unavailable)"
echo "stop.sh: process-tree termination is not confirmed: $survivors" >&2
write_status unconfirmed_stop false "$evidence" "$survivors"
report "termination unconfirmed"
exit 1
