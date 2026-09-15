// Offline check for the ticket-07 fixed-wording graders:  node evals/_harness/ticket07-graders.test.mjs
// Each regex grader must match a reply that uses the skill's fixed wording and fail a reply that
// conveys the same idea without it (the leniency ticket 04's verifier found in llm-only grading).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const grader = (c, g) => fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
const pattern = (c, g) => new RegExp(grader(c, g).match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));
let pass = 0, fail = 0;
const expect = (re, text, want, label) => { if (re.test(text) === want) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const active = pattern("timeout-alive-notice", "override-active");
expect(active, "Timeout override active: 1 minutes (staleness 10 s).", true, "override active line");
expect(active, "The timeout override of 1 minute is in effect.", false, "paraphrase without the fixed wording");

const running = pattern("timeout-alive-notice", "still-running");
expect(running, "Codex still running — 1 min elapsed, last event reasoning 4 s ago; waiting another 1 minutes.", true, "still-running notice");
expect(running, "Codex is making progress, so I kept waiting.", false, "paraphrase without the fixed wording");

const stopped = pattern("timeout-stalled-stop", "stopped-line");
expect(stopped, "Consultation stopped: 1-minute override, 1 min elapsed, no events; options were wait / stop (stop recommended).", true, "stop report");
expect(stopped, "I stopped the consultation because Codex seemed stalled.", false, "paraphrase without the fixed wording");
const stopGrader = grader("timeout-stalled-stop", "used-taskstop");
if (/type: tool_used/.test(stopGrader) && /tool: TaskStop/.test(stopGrader) && /min: 1/.test(stopGrader)) pass++; else { fail++; console.log("FAIL route 1: used-taskstop grader present"); }

for (const [c, value, sample] of [["timeout-override-invalid-text", "abc", 'Timeout override ignored: "abc" is not a positive whole number; using 30 minutes.'],
                                   ["timeout-override-invalid-zero", '"0"', 'Timeout override ignored: "0" is not a positive whole number; using 30 minutes.']]) {
  const ignored = pattern(c, "override-ignored");
  const names = pattern(c, "names-value");
  expect(ignored, sample, true, `${c}: ignored line`);
  expect(ignored, `The override ${value} was not valid, so the default applies.`, false, `${c}: paraphrase without the fixed wording`);
  expect(names, sample, true, `${c}: names the value`);
}
// The zero case must not be satisfied by any other digit string.
expect(pattern("timeout-override-invalid-zero", "names-value"), 'Timeout override ignored: "10" is not valid', false, "zero case does not match \"10\"");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
