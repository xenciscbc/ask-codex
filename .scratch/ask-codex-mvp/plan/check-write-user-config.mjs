// Checks the write-user-config grader regex against JSON-encoded Write inputs.
import fs from "node:fs";
const src = fs.readFileSync("D:/work_data/project/skill/ask-codex/evals/setup-writes-config/graders/write-user-config.md", "utf8");
const pat = src.match(/input_match: '(.*)'/)[1].replace(/''/g, "'");
const re = new RegExp(pat);
const enc = (file_path, content) => JSON.stringify({ file_path, content });
const samples = [
  ["posix user path", enc("/tmp/home/.claude/ask-codex.json", '{"mcp_policy":"allowlist","mcp_allow":["comfyui"]}'), true],
  ["windows user path", enc("C:\\Users\\x\\.claude\\ask-codex.json", '{"mcp_allow":["comfyui"]}'), true],
  ["project file", enc("/tmp/proj/.claude/ask-codex.local.json", '{"mcp_allow":["comfyui"]}'), false],
  ["user path without comfyui", enc("/tmp/home/.claude/ask-codex.json", '{"mcp_allow":["pencil"]}'), false],
];
let failed = 0;
for (const [label, s, want] of samples) {
  const got = re.test(s);
  if (got !== want) failed++;
  console.log(`${got === want ? "ok  " : "FAIL"} ${label}: matched=${got} expected=${want}`);
}
process.exit(failed ? 1 : 0);
