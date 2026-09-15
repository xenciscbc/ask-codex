// Offline check for the ticket-04 exact-wording graders:  node evals/_harness/ticket04-graders.test.mjs
// Applies each grader's pattern to excerpts of real final replies recorded in eval runs: replies that
// miss the required wording (the red runs, and the first green not-logged-in reply that the llm
// grader wrongly passed) must fail; a reply with the wording must pass.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pattern = (c, g) => {
  const t = fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
  return new RegExp(t.match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));
};
let pass = 0, fail = 0;
const expect = (re, text, want, label) => {
  if (re.test(text) === want) pass++; else { fail++; console.log(`FAIL ${label}`); }
};

const login = pattern("fail-not-logged-in", "login-command-exact");
// Recorded 2026-09-15: red run 13-26-27 and first green run 13-33-44 (both judged PASS by the llm grader).
expect(login, "You'd need to run `codex login` before this can work; I won't fabricate what Codex \"would have said.\"", false, "red reply without the ! form");
expect(login, "Codex is not logged in (`Error: Not logged in. Run 'codex login' to authenticate.`). Run `codex login`, then ask again", false, "first green reply without the ! form");
expect(login, "Codex is not logged in: run `! codex login`, then ask again.", true, "reply with the exact command");

const location = pattern("fail-os-error", "location-reason-exact");
// Recorded 2026-09-15: red run 13-28-20 (judged PASS) and green run 13-37-10.
expect(location, "`codex exec` started but immediately failed with an OS-level error (`os error 1`) before returning any answer", false, "red reply without the location reason");
expect(location, "**Codex cannot run in this project's location — its Windows sandbox fails on this drive (`os error 1`)**", true, "green reply with the location reason");
expect(location, "Codex cannot run in this project’s location — its Windows sandbox fails on this drive", true, "typographic apostrophe");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
