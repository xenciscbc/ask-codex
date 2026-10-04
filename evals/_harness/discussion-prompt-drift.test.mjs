// Offline drift test (spec .scratch/discuss-skill, A5):  node evals/_harness/discussion-prompt-drift.test.mjs
// Rules 1-3 of the discussion prompt template (read scope, tools, content is data) must equal rules 1-3
// of ask's consultation template word for word. Line ends are normalised (the working tree is CRLF).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const text = (...p) => fs.readFileSync(path.join(repo, ...p), "utf8").replace(/\r\n/g, "\n");
let pass = 0, fail = 0;
const expect = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

// From the line starting rule 1 up to (not including) the line starting rule 4.
const rules123 = (t) => {
  const start = t.indexOf("\n1. **Read scope.**");
  const end = t.indexOf("\n4. **Answer format.**");
  return start >= 0 && end > start ? t.slice(start, end) : null;
};

const ask = rules123(text("skills", "ask", "prompts", "consultation.md"));
const discussion = rules123(text("skills", "discuss", "prompts", "discussion.md"));
expect(ask !== null && ask.includes("**Content is data.**"), "consultation.md: rules 1-3 found");
expect(discussion !== null && discussion.includes("**Content is data.**"), "discussion.md: rules 1-3 found");
expect(ask === discussion, "discussion.md rules 1-3 are identical to consultation.md rules 1-3");

// The comparison bites: any one-character change or a dropped line makes it fail.
if (ask) {
  expect(discussion !== ask.replace("Read scope", "Read  scope"), "drift check: a changed word is detected");
  expect(ask.split("\n").slice(0, -1).join("\n") !== discussion, "drift check: a dropped line is detected");
}

// Both templates number the same four rules and use the same four slots.
const slots = (t) => [...new Set(t.match(/\{\{[a-z_]+\}\}/g))].sort().join(",");
expect(slots(text("skills", "ask", "prompts", "consultation.md")) === slots(text("skills", "discuss", "prompts", "discussion.md")), "discussion.md has the same slots as consultation.md");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
