#!/usr/bin/env bash
# NUL-delimited argv avoids Windows/MSYS command-line quoting differences.
set -eu
mapfile -d '' -t argv < "$1"
exec "${argv[@]}"
