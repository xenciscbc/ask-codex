// Deterministic negative control for the `no-hypothesis` grader (reliability ticket 07, Plan R07b S5):
//   node evals/_harness/ticket-r07b-s5-control.test.mjs
// `diagnosis-leak-control` is a red-phase control: the user asks to put their hypothesis into the
// question, and the grader is meant to fail on the contaminated prompt. That only happens when the
// model obeys — in the ticket-07 suite run it kept the question blind and the control scored 1.00, so
// the run showed nothing about the grader. This test proves the grader's bite without a model: it
// fails a recorded stdin that carries the hypothesis, in every wording the seeded history allows,
// and passes a blind one. The live control's score is recorded either way and no longer judged.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const norm = (p) => fs.readFileSync(p, "utf8").replace(/\r\n/g, "\n");
let pass = 0, fail = 0;
const expect = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const CASES = ["diagnosis-leak-control", "diagnosis-blind"];
const graders = CASES.map((c) => norm(path.join(evals, c, "graders", "no-hypothesis.md")));
expect(graders[0] === graders[1], "the control and the blind case share one no-hypothesis grader, byte for byte");
const g = graders[0];
expect(/^type: regex$/m.test(g) && /^match: not_contains$/m.test(g), "a not_contains regex grader");
expect(/^\s+source: file$/m.test(g) && /^\s+path: \.stub\/exec-stdin\.txt$/m.test(g), "graded on the stdin the stub recorded, i.e. on what Codex would have received");
const leak = new RegExp(g.match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));

// The hypothesis exists in the fixture, in the user's own words — so a contaminated prompt is possible.
for (const c of CASES) {
  const hist = norm(path.join(evals, c, "history.jsonl")).split("\n").filter(Boolean).map((l) => JSON.parse(l));
  const said = hist.filter((h) => h.type === "user" && typeof h.message.content === "string").map((h) => h.message.content).join("\n");
  expect(/My current hypothesis: the api client drops the Authorization header on retries\./.test(said), `${c}: the seeded history states the hypothesis`);
  expect(leak.test(said), `${c}: the grader finds the hypothesis in the user's own words`);
}
expect(/Include my hypothesis in your question to Codex/.test(norm(path.join(evals, "diagnosis-leak-control", "prompt.md"))),
  "the control's prompt asks for the contamination");

// A blind diagnosis prompt, as step 7 packs it: symptoms, evidence, every failed attempt — no cause.
const BLIND = [
  "Consultation type: diagnosis.",
  "",
  "## Question",
  "Why does fetchUser in src/user.js return an empty object when the API times out, so that the profile page shows 'user not found' for users that exist?",
  "",
  "## Context from Claude",
  "Symptoms: fetchUser returns {} on timeout; src/pages/profile.js renders 'user not found'.",
  "Failed attempts: raising the timeout to 10 seconds — still fails; adding a retry — still fails.",
  "Relevant files: src/user.js, src/pages/profile.js. API_KEY=<withheld>",
].join("\n");
expect(!leak.test(BLIND), "a blind prompt passes (the run is not failed)");

// Contaminated prompts: the hypothesis verbatim, as a leading question, reworded, and lower-cased.
const CONTAMINATED = {
  "verbatim": BLIND + "\nThe user's hypothesis: the api client drops the Authorization header on retries.",
  "leading question": BLIND.replace("users that exist?", "users that exist — could the client be dropping the Authorization header when it retries?"),
  "reworded (auth header)": BLIND + "\nOne idea: the auth header is lost on the second attempt.",
  "reworded (authentication header)": BLIND + "\nCheck whether the authentication header survives a retry.",
  "British spelling": BLIND + "\nPossibly the authorisation header is not re-sent.",
  "lower case": BLIND + "\nmaybe the authorization header goes missing.",
};
for (const [name, text] of Object.entries(CONTAMINATED)) expect(leak.test(text), `contaminated prompt (${name}) is found — the run fails`);

// What the grader does NOT see — recorded, so nobody reads more into a green control than it proves.
expect(!leak.test(BLIND + "\nCould the client be losing its credentials between attempts?"),
  "KNOWN GAP: a hypothesis reworded without 'authorization' / 'auth header' is not found");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
