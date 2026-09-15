#!/usr/bin/env bash
# Run the ask-codex eval suite against the stub `codex`.
#
# Usage: evals/_harness/run-evals.sh [claude plugin eval options...]
#   e.g. evals/_harness/run-evals.sh --case manual-with-question --runs 1 --model claude-sonnet-5 --max-cost-usd 3
#
# Must run where `claude plugin eval` can sandbox Bash (Linux/macOS/WSL; the Windows
# harness refuses shell grants). Guarantees the agent under test can only reach the
# stub: every PATH entry that holds a real `codex` is dropped, the stub directories are
# prepended, and the run aborts unless `codex` resolves to a stub.
#
# The agent's Bash sandbox hides most of the host filesystem, so the stub is copied to
# places it can see: the plugin root (`.eval-stub/`) and each case's `stubbin/`
# (granted to the run via `context.add_dirs`). Both are git-ignored.
#
# Environment:
#   RUN_EVALS_TMPDIR      parent for this run's temp dir (use when the default temp
#                         drive cannot host the eval sandbox, e.g. a RAM disk)
#   RUN_EVALS_DEBUG_FILE  pass --debug-file to claude
set -euo pipefail

repo="$(cd "$(dirname "$0")/../.." && pwd)"
stub_src="$repo/evals/_harness/stub"

# Resolve claude before PATH is rewritten: it may share a directory with a real codex.
claude_bin="$(command -v claude || true)"
if [ -z "$claude_bin" ]; then echo "run-evals: claude not found on PATH" >&2; exit 3; fi

keep=0
for a in "$@"; do [ "$a" = "--keep-temp" ] && keep=1; done

tmp_root="${RUN_EVALS_TMPDIR:-${TMPDIR:-${TEMP:-/tmp}}}"
# PATH is colon-separated, so a Windows-style path (e.g. R:\Temp) must be converted.
if command -v cygpath >/dev/null 2>&1; then tmp_root="$(cygpath -u "$tmp_root")"; fi
mkdir -p "$tmp_root"
run_tmp="$(mktemp -d "$tmp_root/ask-codex-eval.XXXXXX")"
mkdir -p "$run_tmp/tmp"

# Stub copies the sandboxed agent can see.
stub_dirs=("$repo/.eval-stub")
for case_dir in "$repo"/evals/*/; do
  case_dir="${case_dir%/}"
  [ "$(basename "$case_dir")" = "_harness" ] && continue
  [ "$(basename "$case_dir")" = "results" ] && continue
  stub_dirs+=("$case_dir/stubbin")
done
for d in "${stub_dirs[@]}"; do
  mkdir -p "$d"
  cp "$stub_src/codex" "$stub_src/codex-stub.py" "$d/"
  chmod +x "$d/codex"
done

cleanup() {
  rm -rf -- "$repo/.eval-stub"
  for d in "${stub_dirs[@]}"; do rm -rf -- "$d"; done
  if [ "$keep" = 1 ]; then
    echo "run-evals: --keep-temp given; run directory kept at $run_tmp (delete it when done)" >&2
  else
    rm -rf -- "$run_tmp"
  fi
}
trap cleanup EXIT

# The eval harness creates its sandboxes under the temp dir; point it at this run's dir.
export TMPDIR="$run_tmp/tmp"
if command -v cygpath >/dev/null 2>&1; then
  TEMP="$(cygpath -w "$run_tmp/tmp")"; TMP="$TEMP"; export TEMP TMP
fi

newpath="$(IFS=:; echo "${stub_dirs[*]}")"
IFS=: read -r -a parts <<< "$PATH"
for d in "${parts[@]}"; do
  [ -z "$d" ] && continue
  if [ -e "$d/codex" ] || [ -e "$d/codex.cmd" ] || [ -e "$d/codex.exe" ] || [ -e "$d/codex.ps1" ]; then
    echo "run-evals: dropping PATH entry with a real codex: $d" >&2
    continue
  fi
  newpath="$newpath:$d"
done
export PATH="$newpath"

resolved="$(command -v codex || true)"
if [ "$resolved" != "$repo/.eval-stub/codex" ]; then
  echo "run-evals: codex resolves to '$resolved', not the stub — refusing to run" >&2
  exit 3
fi
if [ "$(codex --version)" != "codex-cli 0.0.0-stub" ]; then
  echo "run-evals: stub self-check failed" >&2
  exit 3
fi

global_args=()
if [ -n "${RUN_EVALS_DEBUG_FILE:-}" ]; then global_args+=(--debug-file "$RUN_EVALS_DEBUG_FILE"); fi

eval_args=(--scaffold --no-publish --ablation none)
# Newer Claude Code versions refuse a non-interactive run in an untrusted plugin dir
# unless --trust-plugin is passed; older versions have no trust prompt or flag.
if "$claude_bin" plugin eval --help 2>/dev/null | grep -q -- "--trust-plugin"; then eval_args+=(--trust-plugin); fi

"$claude_bin" "${global_args[@]}" plugin eval "$repo" "${eval_args[@]}" "$@"
