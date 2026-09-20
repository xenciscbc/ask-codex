// Offline check for the slice-04 reply extractor:
//   node .scratch/ask-codex-reliability/plan/live-04-extract-reply.test.mjs
// A synthetic transcript (stream-json and interactive-session lines share this shape) must yield
// the assistant's text blocks in order with the tool calls between them, and nothing else: no
// tool result, no user/system text, no skill body.
import { extract } from "./live-04-extract-reply.mjs";

let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const LINE = "Consultation stopped: interval 1 minutes (override); elapsed 1:14; no events; offered: wait another 1 minutes / stop (recommended: stop); process tree ended";
const lines = [
  { type: "system", subtype: "init", tools: ["Bash"] },
  { type: "user", message: { role: "user", content: "luna Why does parse() drop the last row?" } },
  { type: "assistant", message: { role: "assistant", content: [{ type: "thinking", thinking: "SECRET-THINKING" }, { type: "text", text: "Sending the question to Codex." }, { type: "tool_use", name: "Skill", input: {} }] } },
  { type: "user", message: { role: "user", content: [{ type: "tool_result", content: "SKILL-BODY Consultation stopped: never copy this" }] } },
  { type: "assistant", message: { role: "assistant", content: [{ type: "tool_use", name: "Bash", input: { command: "bash stop.sh" } }] } },
  { type: "user", message: { role: "user", content: [{ type: "tool_result", content: [{ type: "text", text: `TOOL-RESULT ${LINE}` }] }] } },
  { type: "assistant", message: { role: "assistant", content: [{ type: "text", text: LINE }, { type: "tool_use", name: "TaskStop", input: {} }] } },
  { type: "assistant", message: { role: "assistant", content: [{ type: "text", text: `${LINE}\n\nNothing here comes from Codex.` }] } },
  { type: "result", subtype: "success", result: "RESULT-FIELD duplicate of the final text" },
];
const jsonl = lines.map((l) => JSON.stringify(l)).join("\n") + "\nnot json at all\n";

const out = extract(jsonl);
check(out.includes("--- assistant text 1 ---\nSending the question to Codex.\n[tool: Skill]"), "first text block, then its tool call");
check(out.includes("[tool: Bash]\n--- assistant text 2 ---\n" + LINE + "\n[tool: TaskStop]"), "a text-less message still lists its tool; the stop line precedes TaskStop");
check(out.includes("--- assistant text 3 ---\n" + LINE + "\n\nNothing here comes from Codex."), "final reply kept whole");
for (const leak of ["SKILL-BODY", "TOOL-RESULT", "SECRET-THINKING", "RESULT-FIELD", "Why does parse()"]) check(!out.includes(leak), `does not copy ${leak}`);
check((out.match(/--- assistant text \d+ ---/g) ?? []).length === 3, "exactly three text blocks");
check(out.indexOf("[tool: Bash]") < out.indexOf("--- assistant text 2 ---"), "order preserved");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
