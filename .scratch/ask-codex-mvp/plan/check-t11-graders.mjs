// Self-check of the ticket-11 grader regexes that changed after the first green pass.
import fs from "node:fs";
const E = "D:/work_data/project/skill/ask-codex/evals";
const pat = (file, key) => {
  const src = fs.readFileSync(`${E}/${file}`, "utf8");
  return new RegExp(src.match(new RegExp(`${key}: '(.*)'`))[1].replace(/''/g, "'"));
};
const skillFired = pat("policy-default-allowlist/graders/skill-fired.md", "pattern");
const noShell = pat("setup-writes-config/graders/no-shell-workaround.md", "input_match");
const writesProject = pat("setup-project-scope/graders/writes-project-config.md", "input_match");
const enc = (o) => JSON.stringify(o);
const cases = [
  ["skill-fired: Read of project config", skillFired, enc({ file_path: "/w/home/cwd/.claude/ask-codex.local.json" }), true],
  ["skill-fired: Write of user config", skillFired, enc({ file_path: "/w/home/.claude/ask-codex.json" }), true],
  ["skill-fired: disable def", skillFired, 'mcp_servers.x={command=\\"ask-codex-disabled\\"', true],
  ["skill-fired: unrelated", skillFired, enc({ file_path: "src/user.js" }), false],
  ["no-shell: heredoc to user config", noShell, enc({ command: "cat > \"/w/home/.claude/ask-codex.json\" <<'EOF'\n{}\nEOF" }), true],
  ["no-shell: tee to user config", noShell, enc({ command: "echo x | tee /w/home/.claude/ask-codex.json" }), true],
  ["no-shell: ls of user config", noShell, enc({ command: "ls -la /w/home/.claude/ask-codex.json" }), false],
  ["no-shell: test -f", noShell, enc({ command: "test -f \"/w/home/.claude/ask-codex.json\" && echo EXISTS" }), false],
  ["no-shell: redirect elsewhere, then read", noShell, enc({ command: "ls /w 2>/dev/null; cat /w/home/.claude/ask-codex.json" }), false],
  ["no-shell: read with 2>&1", noShell, enc({ command: "cat /w/home/.claude/ask-codex.json 2>&1" }), false],
  ["no-shell: heredoc before redirect", noShell, enc({ command: "cat <<'EOF' > /w/home/.claude/ask-codex.json\n{}\nEOF" }), true],
  ["writes-project: project file with comfyui", writesProject, enc({ file_path: "/w/cwd/.claude/ask-codex.local.json", content: '{"mcp_allow":["comfyui"]}' }), true],
  ["writes-project: user file", writesProject, enc({ file_path: "/w/home/.claude/ask-codex.json", content: '{"mcp_allow":["comfyui"]}' }), false],
  // Hardened in the code-review pass (deferred item (b)): a write is a write, whatever tool does it.
  ["no-shell: cp into user config", noShell, enc({ command: "cp /tmp/new.json /w/home/.claude/ask-codex.json" }), true],
  ["no-shell: mv into user config", noShell, enc({ command: "mv /tmp/new.json /w/home/.claude/ask-codex.json" }), true],
  ["no-shell: tee -a to user config", noShell, enc({ command: "echo x | tee -a /w/home/.claude/ask-codex.json" }), true],
  ["no-shell: append redirect", noShell, enc({ command: "echo x >> /w/home/.claude/ask-codex.json" }), true],
  ["no-shell: python write", noShell, enc({ command: "python3 -c \"open('/w/home/.claude/ask-codex.json','w').write('{}')\"" }), true],
  ["no-shell: sed -i on user config", noShell, enc({ command: "sed -i 's/a/b/' /w/home/.claude/ask-codex.json" }), true],
  ["no-shell: cp of unrelated files", noShell, enc({ command: "cp /tmp/a.txt /tmp/b.txt" }), false],
  ["no-shell: reading with head", noShell, enc({ command: "head -5 /w/home/.claude/ask-codex.json" }), false],
];
let failed = 0;
for (const [label, re, s, want] of cases) {
  const got = re.test(s);
  if (got !== want) failed++;
  console.log(`${got === want ? "ok  " : "FAIL"} ${label}: matched=${got} expected=${want}`);
}
process.exit(failed ? 1 : 0);
