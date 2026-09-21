// Offline check for reliability ticket 10, Plan R07b slice S6b (a wait that blocks):
//   node evals/_harness/ticket-r10-skill.test.mjs
// Step 8 of SKILL.md now orders a foreground wait through the wait script when TaskOutput is
// absent, instead of a background timer the model waits on a notification for (a turn cannot be
// brought back once it ends, in a non-interactive session). This pins the four replaced
// sentences, checks that lines 39 and 41 (untouched by this slice, in the Confirmations section)
// still match the sha256 pins `ticket-r07b-s3-graders.test.mjs` carries, and exercises the two
// headless cases' graders: `no-background-wait` and `final-has-stopped-line`.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repo = path.resolve(evals, "..");
const norm = (p) => fs.readFileSync(p, "utf8").replace(/\r\n/g, "\n");
let pass = 0, fail = 0;
const expect = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

// ---------------------------------------------------------------------------
// 1. Step 8's text: the new bullet, the old wording gone, the other three sentences present.
// ---------------------------------------------------------------------------
const skill = norm(path.join(repo, "skills", "ask", "SKILL.md"));
const skillLines = skill.split("\n");

const NEW_BULLET = "- Otherwise wait with the wait script, in the **foreground** — never start a timer in the background and \"wait for a notification\": your turn ends the moment you stop calling tools, and in a non-interactive session nothing brings you back, so Codex would finish unread and the run directory would stay behind. One line, literal single-quoted paths, Bash `timeout: 600000`: `bash '<skill directory>/scripts/wait.sh' '<tmp>' --seconds <n>` where `<n>` is the time left in the interval in seconds, at most 540 (the Bash tool itself stops a command after 10 minutes). It prints `finished exit=<code> <tmp>` or `still-running elapsed=<n>s <tmp>`; while it prints `still-running` and T has not passed, run it again.";
expect(skill.includes(NEW_BULLET), "SKILL.md carries the new Waiting bullet, word for word");
expect(skillLines.filter((l) => l === NEW_BULLET).length === 1, "the new bullet occurs exactly once, as its own physical line");
expect(!skill.includes("Otherwise start a timer"), "the old bullet opening \"Otherwise start a timer\" no longer occurs in SKILL.md");
expect(!skill.includes("wait for whichever completion notification arrives first"), "\"wait for whichever completion notification arrives first\" is gone from SKILL.md");

const LIVENESS_SENTENCE = "**Check when T has passed.** Judge liveness only from the tracked task's state — without `TaskOutput`, from the wait script's line — and the last event in `<tmp>/events.jsonl` — never from CPU use or process listings:";
expect(skill.includes(LIVENESS_SENTENCE), "the reworded liveness-check sentence is present");

const PARALLEL_SENTENCE = "Both share one interval; without `TaskOutput`, name both run directories in one wait command (`… wait.sh '<tmp1>' '<tmp2>' --seconds <n>`), which returns when both have finished or the time is up.";
expect(skill.includes(PARALLEL_SENTENCE), "the reworded parallel-consultation sentence is present");

const RUNSH_INSERT = "so the stop script can end it, and `<tmp>/exit-code` when the command ends so the wait script can see it;";
expect(skill.includes(RUNSH_INSERT), "the run.sh paragraph carries the exit-code insertion");

// ---------------------------------------------------------------------------
// 2. Lines 39 and 41 (Confirmations section, untouched by this slice) still match the sha256 pins
//    `ticket-r07b-s3-graders.test.mjs` carries — recomputed here, compared against the literals in
//    that file (read, not retyped), so a drift in either file is caught.
// ---------------------------------------------------------------------------
const s3Test = fs.readFileSync(path.join(evals, "_harness", "ticket-r07b-s3-graders.test.mjs"), "utf8");
const pinnedMatch = s3Test.match(/const PINNED_LINES = \{([^}]*)\};/);
expect(!!pinnedMatch, "ticket-r07b-s3-graders.test.mjs still declares PINNED_LINES");
const pinned = {};
for (const m of pinnedMatch[1].matchAll(/(\d+):\s*"([0-9a-f]+)"/g)) pinned[Number(m[1])] = m[2];
const sha = (s) => crypto.createHash("sha256").update(s, "utf8").digest("hex").slice(0, 16);
for (const n of [39, 41]) {
  expect(pinned[n] !== undefined, `PINNED_LINES carries line ${n}`);
  expect(sha(skillLines[n - 1]) === pinned[n], `SKILL.md line ${n} still matches the s3 pin (sha256 ${pinned[n]})`);
}
expect(skillLines.length === 320, "SKILL.md still has 320 lines — every replacement stayed one physical line");

// ---------------------------------------------------------------------------
// 3. The two headless cases' graders exist.
// ---------------------------------------------------------------------------
for (const g of ["used-wait-script", "no-background-wait", "no-taskoutput"]) {
  expect(fs.existsSync(path.join(evals, "headless-timer-wait", "graders", `${g}.md`)), `headless-timer-wait/graders/${g}.md exists`);
  expect(fs.existsSync(path.join(evals, "headless-timer-stall", "graders", `${g}.md`)), `headless-timer-stall/graders/${g}.md exists`);
}
expect(!fs.existsSync(path.join(evals, "headless-timer-wait", "graders", "used-background-timer.md")), "used-background-timer.md was deleted from headless-timer-wait");
expect(fs.existsSync(path.join(evals, "headless-timer-stall", "graders", "final-has-stopped-line.md")), "headless-timer-stall/graders/final-has-stopped-line.md exists");
for (const g of ["skill-fired", "one-codex-exec", "used-run-script", "used-stop-script", "used-taskstop", "temp-cleanup", "no-bare-cd", "stopped-line"]) {
  expect(fs.existsSync(path.join(evals, "headless-timer-stall", "graders", `${g}.md`)), `headless-timer-stall/graders/${g}.md exists`);
}
for (const g of ["stopped-at-stop", "stop-report"]) {
  expect(!fs.existsSync(path.join(evals, "headless-timer-stall", "graders", `${g}.md`)), `headless-timer-stall/graders/${g}.md was NOT copied`);
}

// ---------------------------------------------------------------------------
// 4. `no-background-wait`: fails a background wait.sh or background bare-sleep timer, passes a
//    foreground wait.sh call. Inputs are shaped as the trace stores a Bash tool call's input.
// ---------------------------------------------------------------------------
const read = (c, g) => fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8").replace(/\r\n/g, "\n");
const inputMatch = (c, g) => {
  const t = read(c, g);
  return new RegExp(t.match(/^input_match: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));
};
const cmd = (obj) => JSON.stringify(obj);
for (const c of ["headless-timer-wait", "headless-timer-stall"]) {
  const noBg = inputMatch(c, "no-background-wait");
  expect(/^max: 0$/m.test(read(c, "no-background-wait")), `${c}/no-background-wait allows zero matches`);
  expect(noBg.test(cmd({ command: "sleep 60", run_in_background: true })), `${c}/no-background-wait: a bare 'sleep 60' in the background matches (the run fails)`);
  expect(noBg.test(cmd({ command: "bash '/tmp/ask-codex/run.Ab12Cd/../scripts/wait.sh' '/tmp/ask-codex/run.Ab12Cd' --seconds 200", run_in_background: true })), `${c}/no-background-wait: wait.sh started in the background matches (the run fails)`);
  expect(!noBg.test(cmd({ command: "bash '/plugin/skills/ask/scripts/wait.sh' '/tmp/ask-codex/run.Ab12Cd' --seconds 200" })), `${c}/no-background-wait: a foreground wait.sh call is clean`);
  expect(!noBg.test(cmd({ command: "bash '/plugin/skills/ask/scripts/run.sh' '/tmp/ask-codex/run.Ab12Cd' -- codex exec -s read-only --json - < '/tmp/ask-codex/run.Ab12Cd/prompt.md'", run_in_background: true })), `${c}/no-background-wait: the codex run itself in the background (unrelated to waiting) is clean`);

  const usedWait = inputMatch(c, "used-wait-script");
  expect(usedWait.test(cmd({ command: "bash '/plugin/skills/ask/scripts/wait.sh' '/tmp/ask-codex/run.Ab12Cd' --seconds 200" })), `${c}/used-wait-script: a wait.sh call matches`);
  expect(!usedWait.test(cmd({ command: "sleep 60", run_in_background: true })), `${c}/used-wait-script: a bare sleep timer does not match`);
}

// ---------------------------------------------------------------------------
// 5. `final-has-stopped-line`: PASS on a real stop line (with and without emphasis, with the
//    model's own answer below it), FAIL without the line, FAIL on a NOT-confirmed ending.
// ---------------------------------------------------------------------------
const stoppedLinePattern = read("headless-timer-stall", "final-has-stopped-line").match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'");
const stoppedLine = new RegExp(stoppedLinePattern);
const REAL_LINE = "Consultation stopped: interval 1 minutes (override); elapsed 1:12; last event turn.started 1:10 ago; offered: wait another 1 minutes / stop (recommended: stop); process tree ended";
expect(stoppedLine.test(REAL_LINE), "final-has-stopped-line: PASSes a real stop line");
expect(stoppedLine.test(`**${REAL_LINE.replace("Consultation stopped:", "Consultation stopped:**").replace("process tree ended", "**process tree ended**")}`), "final-has-stopped-line: PASSes the line with markdown emphasis");
expect(stoppedLine.test(`${REAL_LINE}\n\nMy own analysis: the retry loop in fetchUser swallows the timeout error.`), "final-has-stopped-line: PASSes with the model's own answer below the line");
expect(!stoppedLine.test("Codex is still thinking about your question, please wait."), "final-has-stopped-line: FAILs a reply without the line");
expect(!stoppedLine.test("Consultation stopped: interval 1 minutes (override); elapsed 1:12; last event turn.started 1:10 ago; offered: wait another 1 minutes / stop (recommended: stop); process tree NOT confirmed — pids 123"), "final-has-stopped-line: FAILs a reply ending 'process tree NOT confirmed — pids 123'");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
