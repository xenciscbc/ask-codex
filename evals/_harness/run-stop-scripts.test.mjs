// Offline test of the consultation launcher, stopper and foreground wait (reliability tickets 02,
// 03 and 10, Plan R07b slice S6b):
//   node evals/_harness/run-stop-scripts.test.mjs
// Starts the stub in `slow-silent` mode through run.sh with the skill's real command shape and
// redirections, stops it with stop.sh, and checks the pid file, the process tree, events.jsonl,
// exit codes and the report line; then the NOT-confirmed branches and the parallel fields; then
// `run.sh`'s `exit-code` file and `wait.sh`'s foreground, file-based wait over one or more run
// directories.
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
const waitScript = path.join(scripts, "wait.sh");
const runWait = (args) => spawnSync("bash", [waitScript, ...args.map((a) => toBash(a))], { encoding: "utf-8" });
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
  // Finding 1: a flag that is the last token, with no value following it, is a usage error —
  // not an infinite loop (there is no `set -e` and every branch used to `shift 2`).
  {
    const flagsOrder = ["--interval", "--interval-source", "--recommended", "--done", "--still-running"];
    const valuesFor = { "--interval": "30", "--interval-source": "default", "--recommended": "stop", "--done": "gpt-6-astra", "--still-running": "gpt-5.6-sol" };
    for (let i = 0; i < flagsOrder.length; i++) {
      const flag = flagsOrder[i];
      const args = [];
      for (let j = 0; j < i; j++) args.push(flagsOrder[j], valuesFor[flagsOrder[j]]);
      args.push(flag);
      const dir = path.join(root, `missing-value-${flag.replace(/^--/, "")}`);
      fs.mkdirSync(dir);
      const t0 = Date.now();
      const r = stop(dir, args);
      const elapsedMs = Date.now() - t0;
      check(elapsedMs < 3000, `stop.sh: ${flag} with no value returns within 3s, not a hang (took ${elapsedMs}ms)`);
      check(r.status === 2, `stop.sh: ${flag} with no value exits 2 (got ${r.status})`);
      check(r.stderr.length > 0, `stop.sh: ${flag} with no value prints a message on stderr`);
      check(r.stdout === "", `stop.sh: ${flag} with no value prints nothing on stdout (got ${JSON.stringify(r.stdout)})`);
      check(!fs.existsSync(path.join(dir, "stop-request")), `stop.sh: ${flag} with no value creates no stop-request`);
      check(!fs.existsSync(path.join(dir, "stop-report")), `stop.sh: ${flag} with no value creates no stop-report`);
    }
  }

  // ---------------------------------------------------------------------------------------------
  // stop.sh: the launched command already ended by itself (Finding 2a, `exit-code`).
  // ---------------------------------------------------------------------------------------------
  // The command ended on its own (fast `valid` run) before stop.sh is asked to stop it: stop.sh
  // must see `exit-code`, skip killing anything and skip waiting for `stop-result`, then still
  // report the true fact that the tree ended.
  {
    const p = project("already-ended", { exec: { mode: "valid" } });
    const state = launch(p);
    check(await waitFor(() => fs.existsSync(path.join(p.run, "exit-code")), 10000), "already-ended: run.sh writes exit-code once the command ends by itself");
    check(await waitFor(() => state.exited, 5000), "already-ended: run.sh exits");
    const t0 = Date.now();
    const r = stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop"]);
    const elapsedMs = Date.now() - t0;
    const line = reportOf(r);
    check(r.status === 0, `already-ended: exit 0 (got ${r.status}; stderr ${JSON.stringify(r.stderr)})`);
    check(FIELDS.test(line) && /process tree ended$/.test(line), `already-ended: report line ends with 'process tree ended' (got ${JSON.stringify(line)})`);
    check(/already ended by itself with exit status 0/.test(r.stderr), `already-ended: stderr says the command had already ended (got ${JSON.stringify(r.stderr)})`);
    // RESULT_WAIT_S (10s) would not have elapsed if stop.sh waited for stop-result; only the 5s
    // observation window should have run.
    check(elapsedMs < 8000, `already-ended: returns well under RESULT_WAIT_S + the observation window, proving it did not wait for stop-result (took ${elapsedMs}ms)`);
  }
  // Pid reuse is not acted on: after the run has ended by itself, an unrelated, test-owned
  // process stands in for a reused pid. stop.sh must leave it alone (no tree_kill call at all,
  // because exit-code already answers the question) and still report 'ended'.
  {
    const p = project("reused-pid", { exec: { mode: "valid" } });
    launch(p);
    check(await waitFor(() => fs.existsSync(path.join(p.run, "exit-code")), 10000), "reused-pid: exit-code appears");
    // Spawned directly (no shell), so on every platform `.pid` is the real, directly killable
    // pid of this process itself — the same shape `tree_alive`/`tree_kill` act on, without
    // needing the WINPID translation `ps` gives run.sh's own (setsid'd / exec'd) children.
    const unrelated = spawn(process.execPath, ["-e", "setTimeout(() => {}, 65000)"], { stdio: "ignore" });
    await waitFor(() => typeof unrelated.pid === "number", 2000);
    const alive = (pid) => { try { process.kill(pid, 0); return true; } catch { return false; } };
    check(alive(unrelated.pid), "reused-pid: the unrelated process is alive before stop.sh runs");
    const platformField = process.platform === "win32" ? "windows" : "posix";
    fs.writeFileSync(path.join(p.run, "pid"), `pid=${unrelated.pid}\nplatform=${platformField}\nstarted=${Math.floor(Date.now() / 1000)}\n`);
    try {
      const r = stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop"]);
      const line = reportOf(r);
      check(r.status === 0, `reused-pid: exit 0 (got ${r.status}; stderr ${JSON.stringify(r.stderr)})`);
      check(/process tree ended$/.test(line), `reused-pid: reports 'process tree ended' (got ${JSON.stringify(line)})`);
      check(alive(unrelated.pid), "reused-pid: the unrelated (reused-pid) process is still alive after stop.sh — it was not killed");
    } finally {
      try { unrelated.kill(); } catch {}
    }
  }

  // ---------------------------------------------------------------------------------------------
  // run.sh: `exit-code` (ticket 10, S6b).
  // ---------------------------------------------------------------------------------------------
  // A normal (fast) run writes `exit-code` = 0, and a stale one from an earlier run is removed
  // at start.
  {
    const p = project("exit-code-ok", { exec: { mode: "valid" } });
    fs.writeFileSync(path.join(p.run, "exit-code"), "99\n");
    const state = launch(p);
    check(await waitFor(() => state.exited, 10000), "run.sh: exits on a normal (fast) run");
    check(await waitFor(() => fs.existsSync(path.join(p.run, "exit-code")), 5000), "run.sh: writes exit-code");
    check(fs.readFileSync(path.join(p.run, "exit-code"), "utf-8").trim() === "0", "run.sh: exit-code is 0 after a normal run (stale 99 removed at start)");
  }
  // A failing command's real non-zero status is written.
  {
    const p = project("exit-code-fail", { exec: { mode: "fail" } });
    const state = launch(p);
    check(await waitFor(() => state.exited, 10000), "run.sh: exits on a failing run");
    check(await waitFor(() => fs.existsSync(path.join(p.run, "exit-code")), 5000), "run.sh: writes exit-code on a failing run");
    check(fs.readFileSync(path.join(p.run, "exit-code"), "utf-8").trim() === "1", `run.sh: exit-code is the command's real non-zero status (got ${fs.readFileSync(path.join(p.run, "exit-code"), "utf-8")})`);
  }
  // After a stop (stop.sh), exit-code exists too — run.sh writes it before the stop-request block,
  // on every end of the launched command.
  {
    const p = project("exit-code-stop", { exec: { mode: "slow-silent", duration_s: 90 } });
    const state = launch(p);
    check(await waitFor(() => fs.existsSync(path.join(p.run, "pid")), 10000), "exit-code after stop: pid file appears");
    await sleep(1000);
    const r = stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop"]);
    check(r.status === 0, "exit-code after stop: stop.sh confirms the tree ended");
    check(await waitFor(() => state.exited, 5000), "exit-code after stop: run.sh exits");
    check(fs.existsSync(path.join(p.run, "exit-code")), "exit-code after stop: exit-code exists after a stop request");
  }

  // ---------------------------------------------------------------------------------------------
  // wait.sh: foreground, file-based wait (ticket 10, S6b).
  // ---------------------------------------------------------------------------------------------
  const runDir = (name) => { const d = path.join(root, name); fs.mkdirSync(d); return d; };
  const linesOf = (r) => r.stdout.split(/\r?\n/).filter((l) => l.length > 0);

  // A directory that already finished: returns almost at once.
  {
    const d = runDir("wait-finished");
    fs.writeFileSync(path.join(d, "exit-code"), "0\n");
    const t0 = Date.now();
    const r = runWait([d, "--seconds", "5"]);
    const elapsedMs = Date.now() - t0;
    check(r.status === 0, `wait.sh: exit status 0 on a finished directory (got ${r.status}; stderr ${JSON.stringify(r.stderr)})`);
    check(elapsedMs < 2000, `wait.sh: returns within 2s of the run ending (took ${elapsedMs}ms)`);
    check(linesOf(r).length === 1 && linesOf(r)[0] === `finished exit=0 ${toBash(d)}`, `wait.sh: prints 'finished exit=0 <dir>' (got ${JSON.stringify(r.stdout)})`);
  }
  // A never-finishing (slow-silent, run through run.sh) directory: returns at the time limit with
  // 'still-running', and the run is still alive (no exit-code) afterwards.
  {
    const p = project("wait-slow", { exec: { mode: "slow-silent", duration_s: 90 } });
    launch(p);
    check(await waitFor(() => fs.existsSync(path.join(p.run, "pid")), 10000), "wait.sh/slow-silent: pid file appears");
    const t0 = Date.now();
    const r = runWait([p.run, "--seconds", "3"]);
    const elapsedS = (Date.now() - t0) / 1000;
    check(r.status === 0, `wait.sh: exit status 0 on a still-running directory (got ${r.status})`);
    check(elapsedS >= 3 && elapsedS <= 5, `wait.sh: returns after about 3s (took ${elapsedS.toFixed(1)}s)`);
    check(/^still-running elapsed=\d+s /.test(r.stdout) && linesOf(r).length === 1, `wait.sh: prints 'still-running elapsed=<n>s <dir>' (got ${JSON.stringify(r.stdout)})`);
    check(!fs.existsSync(path.join(p.run, "exit-code")), "wait.sh: the run is still alive afterwards (no exit-code yet)");
    stop(p.run, ["--interval", "30", "--interval-source", "default", "--recommended", "stop"]);
  }
  // Two directories, one finished and one running: two lines, in argument order, and the call
  // returns at the time limit (the running one never finishes within it).
  {
    const done = runDir("wait-two-done");
    fs.writeFileSync(path.join(done, "exit-code"), "7\n");
    const running = runDir("wait-two-running");
    const t0 = Date.now();
    const r = runWait([done, running, "--seconds", "2"]);
    const elapsedS = (Date.now() - t0) / 1000;
    check(r.status === 0, "wait.sh: exit status 0 with a mix of finished and still-running directories");
    check(elapsedS >= 2 && elapsedS <= 5, `wait.sh: two directories return at the time limit (took ${elapsedS.toFixed(1)}s)`);
    const ls = linesOf(r);
    check(ls.length === 2 && ls[0] === `finished exit=7 ${toBash(done)}` && new RegExp(`^still-running elapsed=\\d+s ${toBash(running).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`).test(ls[1]), `wait.sh: one line per directory, in argument order (got ${JSON.stringify(r.stdout)})`);
  }
  // Both finished: returns at once.
  {
    const d1 = runDir("wait-both-1"); fs.writeFileSync(path.join(d1, "exit-code"), "0\n");
    const d2 = runDir("wait-both-2"); fs.writeFileSync(path.join(d2, "exit-code"), "3\n");
    const t0 = Date.now();
    const r = runWait([d1, d2, "--seconds", "5"]);
    const elapsedMs = Date.now() - t0;
    check(r.status === 0, "wait.sh: exit status 0 when both directories are already finished");
    check(elapsedMs < 2000, `wait.sh: both finished returns at once (took ${elapsedMs}ms)`);
    const ls = linesOf(r);
    check(ls.length === 2 && ls[0] === `finished exit=0 ${toBash(d1)}` && ls[1] === `finished exit=3 ${toBash(d2)}`, `wait.sh: both lines, in order (got ${JSON.stringify(r.stdout)})`);
  }
  // Usage errors: exit 2, nothing on stdout.
  {
    const d = runDir("wait-usage");
    const noStdout = (r, label) => check(r.status === 2 && r.stdout === "", `wait.sh usage error (${label}): exit 2, empty stdout (status ${r.status}, stdout ${JSON.stringify(r.stdout)})`);
    noStdout(runWait([d, "--seconds", "0"]), "--seconds 0");
    noStdout(runWait([d, "--seconds", "571"]), "--seconds 571");
    noStdout(runWait([d, "--seconds", "abc"]), "--seconds abc");
    noStdout(runWait([d]), "missing --seconds");
    noStdout(runWait(["--seconds", "5", d]), "--seconds before the directories");
    noStdout(runWait(["--seconds", "5"]), "no directory");
    noStdout(runWait([path.join(root, "wait-does-not-exist"), "--seconds", "5"]), "a directory that does not exist");
  }
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
