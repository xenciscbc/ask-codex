#!/usr/bin/env bash
# Windows (Git Bash) end-to-end check of the ask skill against the stub codex — no real Codex call.
# Usage: bash win-stub-run.sh
set -u
REPO='D:/work_data/project/skill/ask-codex'
P=/d/tmp/askcodex-winstub
O="R:/Temp/claude/D--work-data-project-skill-ask-codex/36c44f16-0840-4987-8e42-582b970b27ca/scratchpad/winstub"
S=/d/tmp/askcodex-winstub-bin
rm -rf "$P" "$O" "$S"; mkdir -p "$P/src/pages" "$P/.stub" "$O" "$S"
cp "$REPO/evals/_harness/stub/codex" "$REPO/evals/_harness/stub/codex-stub.py" "$S/"; chmod +x "$S/codex"
cp "$REPO/evals/manual-with-question/scaffold.sh" "$O/scaffold.sh"
( cd "$P" && bash "$O/scaffold.sh" )
# PATH: stub first, every dir holding a real codex removed.
NEWPATH="$S"; IFS=: read -r -a parts <<< "$PATH"
for d in "${parts[@]}"; do [ -z "$d" ] && continue; { [ -e "$d/codex" ] || [ -e "$d/codex.cmd" ] || [ -e "$d/codex.exe" ] || [ -e "$d/codex.ps1" ]; } && continue; NEWPATH="$NEWPATH:$d"; done
CLAUDE_BIN="$(command -v claude)"
echo "stub resolves to: $(PATH="$NEWPATH" command -v codex)"
touch "$O/marker"
( cd "$P" && PATH="$NEWPATH" "$CLAUDE_BIN" -p '/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out, and is that what causes the profile page to show "user not found"?' --plugin-dir "$REPO" --model claude-sonnet-5 --output-format stream-json --verbose --allowedTools Bash Read Glob Grep Write Skill < /dev/null > "$O/stream.jsonl" 2> "$O/stderr.log" ); echo "claude exit=$?"
echo "--- stub records:"; ls -A "$P/.stub"; echo "violations: [$(cat "$P/.stub/violations.log" 2>/dev/null)]"
echo "exec calls recorded: $( [ -f "$P/.stub/exec.sentinel" ] && echo yes || echo no )"
node -e "
const fs=require('fs');const L=fs.readFileSync(process.argv[1],'utf8').split(/\n/).filter(Boolean).map(l=>{try{return JSON.parse(l)}catch{return null}}).filter(Boolean);
let execs=0;for(const m of L){const c=m.message&&Array.isArray(m.message.content)?m.message.content:[];for(const x of c){if(x.type==='tool_use'){const s=JSON.stringify(x.input);if(x.name==='Bash'&&/codex\s+exec/.test(s))execs++;if(x.name==='Write'||x.name==='TaskOutput'||(x.name==='Bash'&&/codex\s+(exec|mcp)|rm -rf|mktemp|cygpath/.test(s)))console.log(x.name+':',s.replace(/\s+/g,' ').slice(0,300));}}
if(m.type==='result')console.log('RESULT cost:',m.total_cost_usd,'turns:',m.num_turns,'codex exec calls:',execs,'\nFINAL:\n'+String(m.result).slice(0,1500));}
" "$O/stream.jsonl"
echo "--- stray dirs: D:/tmp/ask-codex=$( [ -e /d/tmp/ask-codex ] && echo PRESENT || echo absent )"
find R:/Temp /tmp -maxdepth 3 -type d -path "*ask-codex/run.*" -newer "$O/marker" 2>/dev/null | head
rm -rf "$P" "$S"; echo "cleaned: $([ -e "$P" ] || [ -e "$S" ] && echo no || echo yes)"
