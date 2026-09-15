#!/usr/bin/env bash
# Ticket 11 live check (Windows, headless claude -p). One real Codex call (run B).
set -u
REPO='D:/work_data/project/skill/ask-codex'
REAL='C:/Users/admin/.claude/ask-codex.json'
SP='R:/Temp/claude/D--work-data-project-skill-ask-codex/36c44f16-0840-4987-8e42-582b970b27ca/scratchpad/live-11'
P=/d/tmp/askcodex-live-11
TB="$(cygpath -m "${TEMP:-/tmp}")"
state() { if [ -e "$REAL" ]; then echo "present:$(sha256sum "$REAL" | cut -d' ' -f1)"; else echo "absent"; fi; }
restore() {
  echo "!! real user config changed ($1) — restoring and stopping"
  if [ "$S0" = "absent" ]; then rm -f -- "$REAL"; else cp "$SP/real-backup.json" "$REAL"; fi
  echo "after restore: $(state)"; rm -rf "$P"; exit 4
}
rm -rf "$P" "$SP"; mkdir -p "$P/src" "$SP"
cat > "$P/src/user.js" <<'EOF'
export async function fetchUser(id) {
  return await api.get(`/users/${id}`, { timeout: 2000 });
}
EOF
S0="$(state)"; echo "S0 (before run A): $S0"
[ "$S0" != "absent" ] && cp "$REAL" "$SP/real-backup.json" && echo "backup saved"
PERM=(--permission-mode acceptEdits --add-dir "$TB" --allowedTools Bash Read Glob Grep Skill)
echo "permissions: ${PERM[*]}  (file-tool writes: project dir + $TB only)"

echo "=== run A: setup (no Codex call)"
( cd "$P" && claude -p '/ask-codex:setup Scope: project. Mode: allowlist. Allow: comfyui.' --plugin-dir "$REPO" --model claude-sonnet-5 --output-format stream-json --verbose "${PERM[@]}" < /dev/null > "$SP/runA.jsonl" 2> "$SP/runA.err" ); echo "exit=$?"
echo "project file: $(cat "$P/.claude/ask-codex.local.json" 2>/dev/null || echo MISSING)"
if [ ! -f "$P/.claude/ask-codex.local.json" ]; then
  echo "FALLBACK: setup could not write the project config in this headless run (protected .claude/ path); creating it by the test script so run B can proceed"
  mkdir -p "$P/.claude"; printf '%s\n' '{"mcp_policy": "allowlist", "mcp_allow": ["comfyui"]}' > "$P/.claude/ask-codex.local.json"
fi
S1="$(state)"; echo "S1 (after run A): $S1"; [ "$S1" = "$S0" ] || restore "after run A"

echo "=== run B: consultation (1 Codex call)"
( cd "$P" && claude -p '/ask-codex:ask What does the ComfyUI MCP server report about its own status? Use only its server_info tool. I confirm this project'"'"'s ask-codex config .claude/ask-codex.local.json, which allows the MCP server comfyui. Before you clean up, show me every line of events.jsonl that contains mcp_tool_call.' --plugin-dir "$REPO" --model claude-sonnet-5 --output-format stream-json --verbose "${PERM[@]}" < /dev/null > "$SP/runB.jsonl" 2> "$SP/runB.err" ); echo "exit=$?"
S2="$(state)"; echo "S2 (after run B): $S2"; [ "$S2" = "$S0" ] || restore "after run B"

for R in runA runB; do
  node -e "
  const fs=require('fs');const L=fs.readFileSync(process.argv[1],'utf8').split(/\n/).filter(Boolean).map(l=>{try{return JSON.parse(l)}catch{return null}}).filter(Boolean);
  let realWrites=0;
  for(const m of L){const c=m.message&&Array.isArray(m.message.content)?m.message.content:[];for(const x of c){if(x.type!=='tool_use')continue;const s=JSON.stringify(x.input);
    if((x.name==='Write'||x.name==='Edit')&&/Users[\\\\/]+admin[\\\\/]+\.claude[\\\\/]+ask-codex\.json/i.test(s))realWrites++;
    if(x.name==='Write'||x.name==='Edit'||(x.name==='Bash'&&/codex\s+(exec|mcp)|rm -rf/.test(s)))console.log('  '+x.name+':',s.replace(/\s+/g,' ').slice(0,360));}
  if(m.type==='result')console.log('  RESULT cost:',m.total_cost_usd,'turns:',m.num_turns,'\n  FINAL: '+String(m.result).slice(0,1800).replace(/\n/g,'\n  '));}
  console.log('  Write/Edit to the real user config path:',realWrites);
  " "$SP/$R.jsonl"
  echo "  stderr: $(head -3 "$SP/$R.err")"
done
rm -rf "$P"; echo "temp project removed: $([ -e "$P" ] && echo no || echo yes)"; echo "final real-file state: $(state)"
