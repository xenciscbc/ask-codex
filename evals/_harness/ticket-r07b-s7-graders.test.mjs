// Offline check for the graders that replace the LLM judge `presentation` of followup-new-blocking
// (reliability ticket 07, Plan R07b S7(ii)):
//   node evals/_harness/ticket-r07b-s7-graders.test.mjs
// On 2026-09-21 the judge voted 3:0 FAIL on two replies that met its rubric clause by clause (runs 3
// and 4), so the rubric is pinned by deterministic graders instead: C2 unresolved with an updated
// disposition (c2-unresolved, c2-updated), C4 listed separately as a new blocking claim with a
// disposition (heading, c4-shown, c4-under-heading), C5 not presented (c5-not-mentioned, c5-omitted).
// The fixture holds the real final messages of that day's --runs 5.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dir = path.join(evals, "followup-new-blocking", "graders");
const norm = (p) => fs.readFileSync(p, "utf8").replace(/\r\n/g, "\n");
const read = (g) => norm(path.join(dir, `${g}.md`));
const re = (g) => new RegExp(read(g).match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));
const notContains = (g) => /^match: not_contains$/m.test(read(g));
let pass = 0, fail = 0;
const expect = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const TEXT = ["c2-unresolved", "c2-updated", "c4-shown", "heading", "c4-under-heading", "c5-not-mentioned", "c5-omitted"];
expect(!fs.existsSync(path.join(dir, "presentation.md")), "the LLM judge presentation.md is gone");
for (const g of TEXT) expect(fs.existsSync(path.join(dir, `${g}.md`)), `${g}.md exists`);
expect(fs.readdirSync(dir).every((f) => !/^type: llm$/m.test(norm(path.join(dir, f)))), "no LLM judge is left in this case");
// The graders that fail a reply: a `contains` grader that misses it, a `not_contains` grader that finds it.
const failedBy = (text) => TEXT.filter((g) => (notContains(g) ? re(g).test(text) : !re(g).test(text)));

const fixture = path.join(evals, "..", ".scratch", "ask-codex-reliability", "evidence", "07b-s7-followup-replies.json");
const REAL = JSON.parse(norm(fixture));
expect(Object.keys(REAL).length === 5, "five real replies in the fixture");
expect(failedBy(REAL.run1.text).join() === "c5-not-mentioned", "run 1 (says that C5 was omitted): failed by c5-not-mentioned and by nothing else");
for (const k of ["run2", "run3", "run4", "run5"]) {
  const judged = REAL[k].failed.includes("presentation") ? " (the judge had failed it 3:0)" : "";
  expect(failedBy(REAL[k].text).length === 0, `${k}: a reply that meets the rubric passes every text grader${judged}`);
}
expect(REAL.run3.failed.join() === "presentation" && REAL.run4.failed.join() === "presentation", "fixture: runs 3 and 4 were failed by the judge alone");

// What c4-under-heading adds: C4 must come AFTER the heading, and with a disposition.
const c4 = re("c4-under-heading");
const mixed = `${REAL.run2.text.replace("New blocking claim from Codex", "More claims")}\n\nNew blocking claim from Codex\n\n(none)`;
expect(!c4.test(mixed), "C4 mixed in with the carried claims, the heading printed afterwards over nothing → fails");
expect(!c4.test("New blocking claim from Codex\n\nC4 [new-blocking] fetchUser also swallows AbortError."), "C4 under the heading without a disposition → fails");
expect(c4.test("**New blocking claim from Codex**\n\n**C4** `[new-blocking]` fetchUser also swallows AbortError — **reject**. I checked the code."), "bold heading, bold id, a disposition → passes");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
