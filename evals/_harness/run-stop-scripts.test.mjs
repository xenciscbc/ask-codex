// Offline test of the consultation launcher and stopper (reliability tickets 02 and 03):
//   node evals/_harness/run-stop-scripts.test.mjs
// Starts the stub in `slow-silent` mode through run.sh with the skill's real command shape and
// redirections, stops it with stop.sh, and checks the pid file, the process tree, events.jsonl,
// exit codes and the report line; then the NOT-confirmed branches and the parallel fields.
// Needs bash on PATH (Git Bash on Windows) and python for the stub; runs under D:/tmp on Windows.
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..", "..");
const scripts = path.join(repo, "skills", "ask", "scripts");
const stubCodex = path.join(here, "stub", "codex");
const schema = path.join(repo, "skills", "ask", "consultation.schema.json");
const toBash = (p) => p.replace(/\\/g, "/");

if (spawnSync("bash", ["--version"]).status !== 0) { console.log("FAIL bash not found on PATH"); process.exit(1); }

const base = process.platform === "win32" ? "D:/tmp" : os.tmpdir();
fs.mkdirSync(base, { recursive: true });
const root = fs.mkdtempSync(path.join(base, "askcodex-runstop-"));
let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const waitFor = async (pred, ms) => { const t = Date.now(); while (Date.now() - t < ms) { if (pred()) return true; await sleep(100); } return pred(); };

const project = (name, scenario) => {
  const dir = path.join(root, name);
  fs.mkdirSync(path.join(dir, ".stub"), { recursive: true });
  fs.writeFileSync(path.join(dir, ".stub", "scenario.json"), JSON.stringify(scenario));
  const run = path.join(root, `${name}-run`);
  fs.mkdirSync(run);
  fs.writeFileSync(path.join(run, "prompt.md"), "prompt\n");
  return { dir, run };
};
const q = (s) => `'${toBash(s)}'`;
// The skill's step-8 line, with run.sh as its prefix; redirections stay on the caller's line.
const launch = ({ dir, run }) => {
  const cmd = `bash ${q(path.join(scripts, "run.sh"))} ${q(run)} -- ${q(stubCodex)} exec -s read-only --ephemeral --skip-git-repo-check --json -C ${q(dir)} -m gpt-5.6-sol -c 'model_reasoning_effort="high"' --disable apps --output-schema ${q(schema)} -o ${q(path.join(run, "last-message.json"))} - < ${q(path.join(run, "prompt.md"))} > ${q(path.join(run, "events.jsonl"))} 2> ${q(path.join(run, "stderr.log"))}`;
  const child = spawn("bash", ["-c", cmd], { stdio: "ignore" });
  const state = { exited: false, code: null };
  child.on("exit", (code) => { state.exited = true; state.code = code; });
  return state;
};
const stop = (run, args) => spawnSync("bash", [path.join(scripts, "stop.sh"), toBash(run), ...args], { encoding: "utf-8" });
const reportOf = (r) => (r.stdout.split(/\r?\n/).find((l) => l.startsWith("Consultation stopped: ")) || "");
const FIELDS = /^Consultation stopped: interval \d+ minutes \((default|override)\); elapsed \d+:\d\d; (last event [\w.]+ \d+:\d\d ago|no events); offered: wait another \d+ minutes \/ stop \(recommended: (wait|stop)\); process tree (ended|NOT confirmed — pids .+)/;

try {
  // Normal path: a silent run gets killed, verified, reported.
  {
    const p = project("silent", { exec: { mode: "slow-silent", duration_s: 90 } });
    const state = launch(p);
    check(await waitFor(() => fs.existsSync(path.join(p.run, "pid")), 10000), "run.sh: pid file appears");
    check(await waitFor(() => fs.existsSync(path.join(p.run, "events.jsonl")) && fs.statSync(path.join(p.run, "events.jsonl")).size > 0, 10000), "run.sh: events.jsonl receives the stub's first events");
    const pidFile = fs.readFileSync(path.join(p.run, "pid"), "utf-8");
    check(/^pid=\d+$/m.test(pidFile) && /^platform=(windows|posix)$/m.test(pidFile) && /^started=\d+$/m.test(pidFile), `run.sh: pid file has pid, platform, started (got ${JSON.stringify(pidFile)})`);
    await sleep(1500);
    const r = stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop"]);
    const line = reportOf(r);
    check(r.status === 0, `stop.sh: exit 0 (got ${r.status}; stderr ${JSON.stringify(r.stderr)})`);
    check(FIELDS.test(line), `stop.sh: report line has every field (got ${JSON.stringify(line)})`);
    check(/process tree ended$/.test(line), "stop.sh: report ends with 'process tree ended'");
    check(/; last event turn\.started \d+:\d\d ago;/.test(line), "stop.sh: names the stub's last event type");
    check(!/done —/.test(line), "stop.sh: no parallel fields when none were given");
    check(await waitFor(() => state.exited, 5000), "run.sh: exits once its child is gone");
    await sleep(500);
    check(!fs.existsSync(path.join(p.dir, ".stub", "exec-finished")), "stub was killed: no exec-finished");
    const size = fs.statSync(path.join(p.run, "events.jsonl")).size;
    await sleep(1500);
    check(fs.statSync(path.join(p.run, "events.jsonl")).size === size, "events.jsonl stays still after the stop");
    check(fs.existsSync(path.join(p.run, "pid")), "stop.sh: run directory (pid file) not deleted");
    const report = fs.existsSync(path.join(p.run, "stop-report")) ? fs.readFileSync(path.join(p.run, "stop-report"), "utf-8") : "";
    check(report.split(/\r?\n/)[1] === line && !/Parallel check:/.test(report), "stop.sh: stop-report holds the report line for the final answer (no parallel line)");
    // A background job of a non-interactive shell gets /dev/null as stdin unless run.sh keeps it:
    // the prompt (`- < prompt.md`) must reach the command.
    check(fs.existsSync(path.join(p.dir, ".stub", "exec-stdin.txt")) && fs.readFileSync(path.join(p.dir, ".stub", "exec-stdin.txt"), "utf-8").replace(/\r\n/g, "\n") === "prompt\n", "run.sh: the prompt on stdin reaches the command");
  }
  // Cooperative stop (the eval sandbox gives every command its own PID namespace, so stop.sh
  // cannot see the pid): the pid file is rewritten to an unknown pid while run.sh is alive;
  // stop.sh must still end the tree through run.sh and report "ended".
  {
    const p = project("invisible", { exec: { mode: "slow-silent", duration_s: 90 } });
    const state = launch(p);
    check(await waitFor(() => fs.existsSync(path.join(p.run, "pid")), 10000), "cooperative: pid file appears");
    await sleep(1500);
    const pidFile = fs.readFileSync(path.join(p.run, "pid"), "utf-8").replace(/^pid=\d+$/m, "pid=999999");
    fs.writeFileSync(path.join(p.run, "pid"), pidFile);
    const r = stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop"]);
    const line = reportOf(r);
    check(r.status === 0, `cooperative: exit 0 (got ${r.status}; stderr ${JSON.stringify(r.stderr)})`);
    check(/process tree ended$/.test(line), `cooperative: report ends with 'process tree ended' (got ${JSON.stringify(line)})`);
    check(fs.existsSync(path.join(p.run, "stop-request")) && fs.readFileSync(path.join(p.run, "stop-result"), "utf-8").trim() === "ended", "cooperative: run.sh answered the stop request with 'ended'");
    check(await waitFor(() => state.exited, 5000), "cooperative: run.sh exits");
    await sleep(500);
    check(!fs.existsSync(path.join(p.dir, ".stub", "exec-finished")), "cooperative: stub was killed, no exec-finished");
  }
  // run.sh alone reacts to a stop request (what stop.sh relies on).
  {
    const p = project("request", { exec: { mode: "slow-silent", duration_s: 90 } });
    const state = launch(p);
    check(await waitFor(() => fs.existsSync(path.join(p.run, "pid")), 10000), "stop-request: pid file appears");
    await sleep(1000);
    fs.writeFileSync(path.join(p.run, "stop-request"), "");
    check(await waitFor(() => fs.existsSync(path.join(p.run, "stop-result")), 10000), "stop-request: stop-result written");
    check(fs.readFileSync(path.join(p.run, "stop-result"), "utf-8").trim() === "ended", "stop-request: result is 'ended'");
    check(await waitFor(() => state.exited, 5000), "stop-request: run.sh exits");
    await sleep(500);
    check(!fs.existsSync(path.join(p.dir, ".stub", "exec-finished")), "stop-request: no exec-finished");
  }
  // NOT confirmed: the pid file names a process that is not running and no run.sh answers.
  {
    const p = project("dead", {});
    fs.writeFileSync(path.join(p.run, "events.jsonl"), "");
    fs.writeFileSync(path.join(p.run, "pid"), `pid=999999\nplatform=${process.platform === "win32" ? "windows" : "posix"}\nstarted=${Math.floor(Date.now() / 1000) - 65}\n`);
    const r = stop(p.run, ["--interval", "20", "--interval-source", "override", "--recommended", "wait"]);
    const line = reportOf(r);
    check(r.status !== 0, `dead pid: non-zero exit (got ${r.status})`);
    check(FIELDS.test(line) && /process tree NOT confirmed — pids 999999/.test(line), `dead pid: NOT confirmed with the pid (got ${JSON.stringify(line)})`);
    check(/interval 20 minutes \(override\); elapsed 1:0\d; no events; offered: wait another 20 minutes \/ stop \(recommended: wait\)/.test(line), "dead pid: model-supplied fields and elapsed/no-events computed");
    check(!fs.existsSync(path.join(p.run, "stop-result")), "dead pid: nobody answered the stop request");
  }
  // NOT confirmed: no pid file at all; parallel fields appended when given.
  {
    const p = project("nopid", {});
    const r = stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop", "--done", "gpt-6-astra", "--still-running", "gpt-5.6-sol"]);
    const line = reportOf(r);
    check(r.status !== 0, `no pid file: non-zero exit (got ${r.status})`);
    check(/process tree NOT confirmed — pids none recorded; done — gpt-6-astra; still running — gpt-5\.6-sol$/.test(line), `no pid file: NOT confirmed plus parallel fields at the end (got ${JSON.stringify(line)})`);
    const r2 = stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop", "--done", "none", "--still-running", "gpt-5.6-sol"]);
    check(/; done — none; still running — gpt-5\.6-sol$/.test(reportOf(r2)), "parallel fields: 'done — none' passes through");
    check(/^Parallel check: done — none; still running — gpt-5\.6-sol\.$/m.test(fs.readFileSync(path.join(p.run, "stop-report"), "utf-8")), "parallel: stop-report carries the Parallel check line");
  }
  // Argument errors never print a report line.
  {
    const r = stop(path.join(root, "nopid-run"), ["--interval", "30"]);
    check(r.status === 2 && reportOf(r) === "", "missing arguments: usage error, no report line");
  }
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
