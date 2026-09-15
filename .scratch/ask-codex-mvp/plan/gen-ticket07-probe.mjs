// Generates the ticket-07 tool probe (and, only if TaskOutput is unusable, the notification probe).
// Usage: node gen-ticket07-probe.mjs [tools|notify]
import fs from "node:fs";
import path from "node:path";

const EVALS = "D:/work_data/project/skill/ask-codex/evals";
const PROBES = {
  tools: {
    name: "task-tools-probe", desc: "Probe (no skill): are TaskOutput and TaskStop usable in an eval child with the ticket-07 grant?",
    tools: "[Bash, TaskOutput, TaskStop]",
    prompt: "Start `sleep 120` with Bash `run_in_background: true`. Call `TaskOutput` on that task with `block: true` and `timeout: 5000` and report the status it returns. Then call `TaskStop` on it and report the result.",
    graders: {
      "used-taskoutput": "---\ntype: tool_used\ntool: TaskOutput\nmin: 1\n---\n",
      "used-taskstop": "---\ntype: tool_used\ntool: TaskStop\nmin: 1\n---\n",
      "reported": "---\ntype: llm\n---\n\nPASS if the final response reports that the background task was still running when checked and that it was then stopped.\nFAIL if it says a tool was unavailable, or does not report both the status and the stop.\n",
    },
  },
  notify: {
    name: "bg-notify-probe", desc: "Probe (no skill): does a background Bash completion notification wake the headless child without ending the turn?",
    tools: "[Bash]",
    prompt: "Start `sleep 20` with Bash `run_in_background: true`. Do not call any tool while it runs. When its completion notification arrives, reply with the single word NOTIFIED.",
    graders: {
      "notified": "---\ntype: regex\npattern: 'NOTIFIED'\n---\n",
      "one-bash": "---\ntype: tool_used\ntool: Bash\nmin: 1\nmax: 1\n---\n",
    },
  },
};

const which = process.argv[2] || "tools";
const p = PROBES[which];
const dir = path.join(EVALS, p.name);
fs.rmSync(dir, { recursive: true, force: true });
fs.mkdirSync(path.join(dir, "graders"), { recursive: true });
fs.writeFileSync(path.join(dir, "case.yaml"), `schema_version: "1.1"\nname: ${p.name}\ntags: [ticket-07]\ncontext:\n  scaffold_script: scaffold.sh\n  add_dirs: [stubbin]\n`);
fs.writeFileSync(path.join(dir, "prompt.md"), `---\ndescription: ${JSON.stringify(p.desc)}\nmax_turns: 10\ntimeout_seconds: 300\nallowed_tools: ${p.tools}\n---\n\n${p.prompt}\n`);
fs.writeFileSync(path.join(dir, "scaffold.sh"), "#!/usr/bin/env bash\nset -euo pipefail\nmkdir -p .stub\necho '{}' > .stub/scenario.json\n", { mode: 0o755 });
for (const [g, c] of Object.entries(p.graders)) fs.writeFileSync(path.join(dir, "graders", `${g}.md`), c);
console.log(`${p.name}: ${Object.keys(p.graders).length} graders`);
