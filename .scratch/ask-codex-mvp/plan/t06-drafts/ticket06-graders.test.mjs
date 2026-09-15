// Offline check for ticket 06 (copy to evals/_harness/ once slice 06 starts):
//   node evals/_harness/ticket06-graders.test.mjs
// 1. Prompt assembly: core + follow-up framing has no unconditional "followup_status = null" rule;
//    core + each initial framing still requires null.
// 2. stdin graders bind the carried claim's id to its content and disposition.
// 3. last-message graders need the fixed status lines; case 2's `loadUser` grader fires on any mention.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const evals = path.join(repo, "evals");
const read = (p) => fs.readFileSync(path.join(repo, p), "utf8");
const grader = (c, g) => {
  const t = fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
  return new RegExp(t.match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));
};
let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

// 1. prompt assembly
const core = read("skills/ask/prompts/consultation.md");
const assemble = (t) => core.replace("{{framing}}", read(`skills/ask/prompts/framing/${t}.md`));
const UNCONDITIONAL_NULL = /`followup_status` = `null`(?![^\n]*unless)/;
const follow = assemble("follow-up");
check(!UNCONDITIONAL_NULL.test(follow), "follow-up prompt has no unconditional null rule");
check(/resolved/.test(follow) && /new-blocking/.test(follow), "follow-up prompt states the follow-up statuses");
for (const t of ["second-opinion", "targeted-check", "diagnosis", "technical-question"]) {
  const p = assemble(t);
  check(/`followup_status` = `null`/.test(p), `${t} prompt still requires null`);
  check(!/new-blocking/.test(p), `${t} prompt carries no follow-up status rules`);
}

// 2. stdin graders (case 1)
const LINE = grader("followup-carries-claims", "stdin-c2-line");
const REASON = grader("followup-carries-claims", "stdin-c2-reason");
const NOT_C1 = grader("followup-carries-claims", "not-carried-c1");
const carried = "C2 [investigate] renderProfile treats an empty object as 'user not found' — Claude: not yet confirmed that no other path renders it";
check(!LINE.test(follow) && !REASON.test(follow), "core + framing without carried claims fails the C2 line graders");
check(LINE.test(carried) && REASON.test(carried), "a correct carried line passes");
check(!REASON.test("C2 [investigate] renderProfile treats an empty object as 'user not found'"), "a carried line without the reason fails");
check(NOT_C1.test(`C1 [adopt] fetchUser catches TimeoutError — Claude: matches the code\n${carried}`), "carrying C1 [adopt] is detected");

// 3. last-message graders
const RESOLVED = grader("followup-carries-claims", "c2-resolved");
check(RESOLVED.test("C2 [resolved] renderProfile … — Updated disposition: adopt — confirmed"), "C2 [resolved] passes case 1");
check(!RESOLVED.test("C2 [unresolved] renderProfile … — Updated disposition: investigate — still open"), "C2 [unresolved] does not pass case 1");
check(!RESOLVED.test("C2 renderProfile … — Updated disposition: adopt"), "a line without the status fails");
const UNRES = grader("followup-new-blocking", "c2-unresolved");
check(UNRES.test("C2 [unresolved] renderProfile … — Updated disposition: investigate — still open"), "C2 [unresolved] passes case 2");
const HEADING = grader("followup-new-blocking", "heading");
check(HEADING.test("New blocking claim from Codex\n- C4 …"), "heading present passes");
check(!HEADING.test("C4 is new and blocking: …"), "no heading fails");
const LOADUSER = grader("followup-new-blocking", "c5-omitted");
check(LOADUSER.test("Out of scope: Codex also suggested renaming fetchUser to loadUser."), "any mention of loadUser is caught");

// argv
const RESUME = grader("followup-carries-claims", "no-resume");
check(RESUME.test('["exec", "resume", "--last"]'), "an argv with resume is caught");
check(!RESUME.test('["exec", "-s", "read-only", "--ephemeral"]'), "a normal argv is not");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
