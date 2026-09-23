// Offline check for the reliability ticket-05 graders (the fixed model-scope line):
//   node evals/_harness/ticket-r05-graders.test.mjs
// `scope-line` must pass the exact line (plain, bold, backticked values) and fail an alias-only
// slug, a missing effort and a sentence that paraphrases it; `no-scope-line` is a not_contains
// grader on the same fixed words, so the control case fails as soon as the line appears.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (c, g) => fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
const pattern = (c, g) => new RegExp(read(c, g).match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));
let pass = 0, fail = 0;
const expect = (re, text, want, label) => { if (re.test(text) === want) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const line = pattern("alias-astra", "scope-line");
const LINE = "Model choice applies to this consultation only: gpt-6-astra, effort medium.";
for (const [label, text, want] of [
  ["exact line", LINE, true],
  ["inside a reply, on its own line", `Asked: why fetchUser returns {} — a diagnosis, answered by gpt-6-astra at medium.\n${LINE}\nMCP: all servers disabled for this consultation.`, true],
  ["bold fixed words", "**Model choice applies to this consultation only:** gpt-6-astra, effort medium.", true],
  ["backticked values", "Model choice applies to this consultation only: `gpt-6-astra`, effort `medium`.", true],
  ["whole line in backticks", "`Model choice applies to this consultation only: gpt-6-astra, effort medium.`", true],
  ["alias instead of the full slug", "Model choice applies to this consultation only: astra, effort medium.", false],
  ["effort missing", "Model choice applies to this consultation only: gpt-6-astra.", false],
  ["wrong model", "Model choice applies to this consultation only: gpt-6-sol, effort medium.", false],
  ["rewritten as a sentence", "The model you chose (gpt-6-astra, medium effort) applies only to this consultation.", false],
  ["translated", "模型選擇只適用於這次諮詢：gpt-6-astra，effort medium。", false],
]) expect(line, text, want, `scope-line: ${label} → ${want ? "pass" : "fail"}`);

const none = read("override-restated-no-prompt", "no-scope-line");
expect(/^match: not_contains$/m, none, true, "no-scope-line is a not_contains grader");
const absent = pattern("override-restated-no-prompt", "no-scope-line");
expect(absent, LINE, true, "no-scope-line: its pattern finds the fixed line (so the grader fails the run)");
expect(absent, "**Model choice applies to this consultation only:** `gpt-6-astra`, effort medium.", true, "no-scope-line: finds the bold form");
expect(absent, "Asked: why fetchUser returns {} — answered by gpt-6-astra at medium.\nMCP: all servers disabled for this consultation.", false, "no-scope-line: a reply without the line is clean");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
