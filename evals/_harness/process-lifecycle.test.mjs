// Focused process integration for script-owned consultation lifecycle.
// Uses the real Git for Windows bash explicitly; never accepts system32/WSL bash.
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..", "..");
const scripts = path.join(repo, "skills", "ask", "scripts");
const runScript = path.join(scripts, "run.sh");
const stopScript = path.join(scripts, "stop.sh");
const bash = process.platform === "win32"
  ? "C:\\Program Files\\Git\\bin\\bash.exe"
  : "/bin/bash";

if (!fs.existsSync(bash)) throw new Error(`supported bash not found: ${bash}`);
if (process.platform === "win32" && /system32/i.test(bash)) throw new Error("test selected system/WSL bash");

const gitRoot = process.platform === "win32" ? path.dirname(path.dirname(bash)) : "";
const env = {
  ...process.env,
  PATH: process.platform === "win32"
    ? `${path.join(gitRoot, "usr", "bin")};${path.join(gitRoot, "bin")};${process.env.PATH ?? ""}`
    : process.env.PATH,
  ASK_CODEX_STOP_WINDOW_S: "0",
  ASK_CODEX_STOP_RESULT_WAIT_S: "4",
};
const toBash = (p) => p.replace(/\\/g, "/");
const base = process.platform === "win32" ? path.join(repo, ".scratch") : os.tmpdir();
fs.mkdirSync(base, { recursive: true });
const root = fs.mkdtempSync(path.join(base, "askcodex-lifecycle-"));
let passed = 0;
const check = (condition, message) => {
  if (!condition) throw new Error(message);
  passed += 1;
};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const waitFor = async (predicate, timeoutMs) => {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    if (predicate()) return true;
    await sleep(50);
  }
  return predicate();
};
const launch = (dir, script, extraEnv = {}) => {
  const child = spawn(bash, [toBash(runScript), toBash(dir), "--", "bash", "-c", script], {
    env: { ...env, ...extraEnv },
    stdio: "ignore",
  });
  const completion = new Promise((resolve) => child.once("exit", (code, signal) => resolve({ code, signal })));
  return { child, completion };
};
const stop = (dir, { offered = true } = {}) => {
  const args = [
    toBash(stopScript), toBash(dir),
    "--interval", "30", "--interval-source", "default", "--recommended", "stop",
  ];
  if (offered) args.push("--offered", "wait,stop");
  return spawnSync(bash, args, { env, encoding: "utf8", timeout: 15000 });
};
const makeRun = (name) => {
  const dir = path.join(root, name);
  fs.mkdirSync(dir);
  return dir;
};
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));

try {
  // Normal completion reaps the identity watcher before returning, so the directory is no
  // longer held open by a helper that inherited the launcher's handles.
  {
    const dir = makeRun("normal");
    const state = launch(dir, "sleep 0.3");
    const result = await state.completion;
    check(result.code === 0, `normal launcher exit: ${JSON.stringify(result)}`);
    check(fs.readFileSync(path.join(dir, "exit-code"), "utf8").trim() === "0", "normal exit-code recorded");
    check(readJson(path.join(dir, "launcher-result.json")).exit_code === 0, "durable launcher result is written after watcher shutdown");
    fs.rmSync(dir, { recursive: true });
    check(!fs.existsSync(dir), "normal run directory can be removed immediately after launcher exit");
  }

  // Reproduce the former race: root and descendant are killed first, verification is delayed,
  // and the root exits promptly. run.sh must wait for the watcher to publish stop-result.
  {
    const dir = makeRun("race");
    const state = launch(
      dir,
      "trap '' TERM; (trap '' TERM; sleep 30) & wait",
      { ASK_CODEX_TREE_VERIFY_DELAY_S: "2" },
    );
    check(await waitFor(() => fs.existsSync(path.join(dir, "process-identities")), 10000), "race identities captured");
    await sleep(500);
    const requestedAt = Date.now();
    fs.writeFileSync(path.join(dir, "stop-request"), "");
    const result = await state.completion;
    const elapsed = Date.now() - requestedAt;
    check(elapsed >= 1500, `launcher waited for delayed verification (${elapsed}ms)`);
    check(elapsed < 10000, `stop terminated the command promptly (${elapsed}ms)`);
    check(result.code !== null || result.signal !== null, "terminated command result is collected");
    const verified = fs.existsSync(path.join(dir, "process-identities.verified"));
    const stopResult = fs.readFileSync(path.join(dir, "stop-result"), "utf8").trim();
    check(verified ? stopResult === "ended" : stopResult.startsWith("unconfirmed "), `watcher reported verification evidence honestly: ${stopResult}`);
    check(typeof readJson(path.join(dir, "launcher-result.json")).exit_code === "number", "stopped launcher publishes durable completion after cleanup");
  }

  // Cancellation can arrive immediately after Popen, before run.sh initializes its files.
  {
    const dir = makeRun("early-cancel");
    fs.writeFileSync(path.join(dir, "stop-request"), "");
    const started = Date.now();
    const state = launch(dir, "sleep 30");
    await state.completion;
    check(Date.now() - started < 10000, "preexisting stop-request is preserved and honored promptly");
    check(fs.existsSync(path.join(dir, "stop-result")), "early cancellation produces a stop result");
    check(fs.existsSync(path.join(dir, "launcher-result.json")), "early cancellation produces durable launcher completion");
  }

  // POSIX regression: a root that exits immediately must not abandon a TERM-resistant child in
  // its setsid group, even when the first descendant scan races with the root exit.
  if (process.platform !== "win32") {
    const dir = makeRun("root-exit-child");
    const childPidFile = path.join(dir, "child-pid");
    const state = launch(dir, `(trap '' TERM; sleep 30) & echo $! > '${toBash(childPidFile)}'; exit 0`);
    const result = await state.completion;
    check(result.code === 0, "POSIX root preserves its own successful status");
    const childPid = Number(fs.readFileSync(childPidFile, "utf8").trim());
    let alive = true;
    try { process.kill(childPid, 0); } catch { alive = false; }
    check(!alive, "POSIX normal root exit cleans the surviving process-group child");
  }

  // A child may create its own session while its original parent is still running. The launcher
  // must retain that descendant's identity and stop it individually; an empty root process group
  // cannot by itself prove whole-tree termination.
  if (process.platform !== "win32") {
    const dir = makeRun("detached-descendant");
    const childPidFile = path.join(dir, "detached-child-pid");
    const fixture = path.join(dir, "detached-root.py");
    fs.writeFileSync(fixture, [
      "import pathlib, subprocess, sys, time",
      "child = subprocess.Popen([sys.executable, '-c', 'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'], start_new_session=True)",
      "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8')",
      "time.sleep(60)",
    ].join("\n"));
    const state = launch(dir, `python3 '${toBash(fixture)}' '${toBash(childPidFile)}'`);
    let childPid = 0;
    const alive = () => {
      if (!childPid) return false;
      try { process.kill(childPid, 0); return true; } catch { return false; }
    };
    try {
      check(await waitFor(() => fs.existsSync(childPidFile), 10000), "detached descendant publishes its pid");
      childPid = Number(fs.readFileSync(childPidFile, "utf8"));
      check(alive(), "detached descendant is alive before stop");
      await sleep(750);
      const result = stop(dir);
      const status = readJson(path.join(dir, "stop-status.json"));
      check((result.status === 0) === status.confirmed, "detached stop exit matches structured confirmation");
      await state.completion;
      await waitFor(() => !alive(), 3000);
      check(status.confirmed === true, `detached descendant stop is positively verified (${status.termination.evidence})`);
      check(!alive(), "confirmed detached-descendant stop independently observes the child dead");
    } finally {
      if (alive()) { try { process.kill(childPid, "SIGKILL"); } catch {} }
      if (!fs.existsSync(path.join(dir, "launcher-result.json")) && fs.existsSync(path.join(dir, "pid"))) {
        try { stop(dir); } catch {}
      }
      try { state.child.kill(); } catch {}
    }
  }

  // A caller that cannot see the recorded root still gets the in-namespace watcher's answer.
  {
    const dir = makeRun("cooperative");
    const state = launch(dir, "sleep 30");
    check(await waitFor(() => fs.existsSync(path.join(dir, "pid")), 10000), "cooperative pid recorded");
    await sleep(500);
    const pidFile = fs.readFileSync(path.join(dir, "pid"), "utf8").replace(/^pid=\d+$/m, "pid=999999");
    fs.writeFileSync(path.join(dir, "pid"), pidFile);
    const result = stop(dir);
    const status = readJson(path.join(dir, "stop-status.json"));
    check((result.status === 0) === status.confirmed, `cooperative exit matches structured verification: ${result.status}`);
    check(status.interval_minutes === 30 && status.options_offered.join(",") === "wait,stop", "structured timer and offered actions recorded");
    await state.completion;
    const stopResult = fs.readFileSync(path.join(dir, "stop-result"), "utf8").trim();
    check(status.confirmed ? stopResult === "ended" : stopResult.startsWith("unconfirmed "), "cooperative watcher publishes a truthful result");
  }

  // exit-code is execution state, not termination proof. With no captured identities the stop
  // remains unconfirmed and retains the run location for diagnosis.
  {
    const dir = makeRun("exit-is-not-proof");
    fs.writeFileSync(path.join(dir, "pid"), `pid=999999\nplatform=${process.platform === "win32" ? "windows" : "posix"}\nstarted=${Math.floor(Date.now() / 1000)}\nidentity=old\n`);
    fs.writeFileSync(path.join(dir, "process-identities"), "999999|old\n");
    fs.writeFileSync(path.join(dir, "exit-code"), "0\n");
    const result = stop(dir, { offered: false });
    check(result.status !== 0, "exit-code without identity evidence is unconfirmed");
    const status = readJson(path.join(dir, "stop-status.json"));
    check(status.status === "unconfirmed_stop" && status.confirmed === false, "unconfirmed status is explicit");
    check(status.termination.exit_code_present === true && status.termination.evidence === "root_identity_unmatched", "exit-code presence without owned-tree evidence cannot prove termination");
    check(status.options_offered.length === 0, "structured status defaults to no options actually offered");
    check(status.retained_location === toBash(dir) || status.retained_location === dir, "unconfirmed run reports retained location");
  }

  // Once the original identities are known absent, a reused numeric pid is never signalled.
  {
    const dir = makeRun("reused-pid");
    const state = launch(dir, "sleep 0.3");
    await state.completion;
    check(fs.existsSync(path.join(dir, "process-identities")), "original identity record retained");
    const unrelated = spawn(process.execPath, ["-e", "setTimeout(() => {}, 30000)"], { stdio: "ignore" });
    const alive = () => { try { process.kill(unrelated.pid, 0); return true; } catch { return false; } };
    check(alive(), "unrelated replacement process starts");
    const oldPid = fs.readFileSync(path.join(dir, "pid"), "utf8");
    fs.writeFileSync(path.join(dir, "pid"), oldPid.replace(/^pid=\d+$/m, `pid=${unrelated.pid}`));
    try {
      const result = stop(dir);
      check(result.status !== 0, `identity-based stop rejects rewritten root identity: ${result.stderr}`);
      check(alive(), "reused pid process was not killed");
      const status = readJson(path.join(dir, "stop-status.json"));
      check(status.termination.evidence === "root_identity_unmatched", "status names the reused-root identity mismatch");
    } finally {
      unrelated.kill();
    }
  }
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}

console.log(`${passed} lifecycle assertions passed`);
