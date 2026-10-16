#!/usr/bin/env bash
# One headless turn of the C7 live session. Usage: turn.sh <name> <cwd> <prompt-file> [<session id to resume>]
name="$1"; cwd="$2"; prompt="$(cat "$3")"; resume="$4"
cd "$cwd" || exit 2
args=(-p --output-format json --plugin-dir 'D:/work_data/project/skill/ask-codex'
      --settings '{"enabledPlugins":{"ask-codex@ask-codex":false}}'
      --allowedTools Bash Write Read TaskOutput TaskStop)
if [ -n "$resume" ]; then args+=(--resume "$resume"); fi
claude "${args[@]}" < "$3" > "/d/tmp/c7-live/$name.json" 2> "/d/tmp/c7-live/$name.err"
echo "exit=$?"
