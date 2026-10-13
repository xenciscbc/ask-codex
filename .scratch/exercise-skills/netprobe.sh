#!/usr/bin/env bash
# Q29/Q30 probe: what can a command inside `codex sandbox` reach, per configuration. No model call.
# Needs 127.0.0.1:8765 and :8766 serving t.txt. Usage: bash netprobe.sh
cd /d/tmp/netprobe || exit 1

probe() {  # label, then codex -c args
  local label=$1; shift
  echo "=== $label"
  codex sandbox "$@" cmd /c "set" 2>&1 | grep -i -E "^(https?_proxy|all_proxy|no_proxy)=" | sed 's/^/  env: /'
  for url in http://127.0.0.1:8765/t.txt http://127.0.0.1:8766/t.txt http://localhost:8765/t.txt https://example.com/; do
    printf '  %-34s via-proxy: ' "$url"
    codex sandbox "$@" curl.exe -sS -m 8 -o - -w " [%{http_code}]" "$url" 2>&1 | tr -d '\r\n' | cut -c1-90
    printf '\n  %-34s direct:    ' ""
    codex sandbox "$@" curl.exe -sS -m 8 --noproxy "*" -o - -w " [%{http_code}]" "$url" 2>&1 | tr -d '\r\n' | cut -c1-90
    echo
  done
}

PROXY=(-c 'default_permissions="probe"' -c 'permissions.probe.extends=":read-only"'
       -c 'permissions.probe.network.enabled=true' -c 'features.network_proxy.enabled=true'
       -c 'permissions.probe.network.allow_local_binding=false')

probe "T1 default (read-only, network off)"
probe "T2 proxy, no allow rules" "${PROXY[@]}"
probe "T3 proxy, allow 127.0.0.1" "${PROXY[@]}" -c 'permissions.probe.network.domains={"127.0.0.1"="allow"}'
probe "T4 proxy, allow 127.0.0.1:8765" "${PROXY[@]}" -c 'permissions.probe.network.domains={"127.0.0.1:8765"="allow"}'
