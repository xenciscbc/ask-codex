// Slice 04: watch one live stop scenario from outside the Claude session (Windows only).
//   node .scratch/ask-codex-reliability/plan/live-04-watch.mjs --scenario H --marker ask-codex-live-04 --out <watch.json> [--leaf codex.exe] [--max-minutes 20]
// Start it BEFORE the scenario. It finds the scenario's leaf process (default codex.exe) by a
// marker in its command line (the workspace path), takes the run directory from its
// `-o <run dir>/last-message.json` argument and the tree's root from `<run dir>/pid` (written by
// run.sh), and records:
//   - processes, about once a second (one long-lived PowerShell, Get-CimInstance Win32_Process):
//     the baseline leaf set, every member of the tree ever seen (pid + creation time, so a reused
//     pid is not a survivor) with its last-seen time, who is alive 5 s and 60 s after the stop;
//   - files, every 250 ms (fs.stat only): the size of events.jsonl and the first time each of
//     stop-request, stop-report and last-message.json exists, until the run directory is gone.
// Command lines are stored for the scenario's own chain only. Judged by live-04-check.mjs.
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const arg = (name, dflt) => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : dflt; };
const scenario = arg("scenario", "X");
const marker = (arg("marker") ?? "").toLowerCase();
const outFile = arg("out");
const leaf = arg("leaf", "codex.exe").toLowerCase();
const maxMs = Number(arg("max-minutes", "20")) * 60_000;
if (!marker || !outFile) { console.error("usage: live-04-watch.mjs --scenario <H|I> --marker <text in the leaf's command line> --out <file> [--leaf codex.exe] [--max-minutes 20]"); process.exit(2); }

const t0 = Date.now();
const now = () => Date.now() - t0;
const key = (p) => `${p.i}@${p.c}`;
const norm = (s) => String(s ?? "").replace(/\\/g, "/").toLowerCase();

const state = {
  scenario, marker, leaf, startedAt: new Date(t0).toISOString(), samples: 0,
  runDir: null, rootSource: null, baselineCodex: null, chain: [],
  moments: { leafSeenMs: null, stopRequestedMs: null, chainGoneMs: null, reportedMs: null, lastMessageMs: null, runDirGoneMs: null },
  aliveAt5: null, aliveAt60: null, codexAt60: null, eventsSeries: [],
};
const members = new Map(); // key → chain entry
let rootPid = null, fileTimer = null, finished = false, prevSampleMs = 0;

const PS = `
$ErrorActionPreference = 'SilentlyContinue'
while ($true) {
  $rows = Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,Name,CreationDate,CommandLine | ForEach-Object {
    $c = $null; if ($_.CreationDate) { $c = $_.CreationDate.ToUniversalTime().ToString('o') }
    $l = $null; if ($_.Name -eq '${leaf}') { $l = $_.CommandLine }
    [pscustomobject]@{ i = $_.ProcessId; p = $_.ParentProcessId; n = $_.Name; c = $c; l = $l }
  }
  [Console]::Out.WriteLine((ConvertTo-Json @($rows) -Compress))
  Start-Sleep -Milliseconds 400
}`;
const ps = spawn("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", PS], { stdio: ["ignore", "pipe", "inherit"] });

function runDirFrom(cmd) {
  const m = String(cmd).match(/-o\s+["']?([^"']+?)[\\/]last-message\.json/);
  if (!m) return null;
  return m[1].replace(/^\/([a-zA-Z])\//, (_, d) => `${d.toUpperCase()}:/`);
}

function watchFiles() {
  const dir = state.runDir;
  const first = (name, moment) => { if (state.moments[moment] == null && fs.existsSync(path.join(dir, name))) state.moments[moment] = now(); };
  fileTimer = setInterval(() => {
    if (!fs.existsSync(dir)) {
      if (state.moments.runDirGoneMs == null) state.moments.runDirGoneMs = now();
      clearInterval(fileTimer);
      return;
    }
    first("stop-request", "stopRequestedMs");
    first("stop-report", "reportedMs");
    first("last-message.json", "lastMessageMs");
    let size = null;
    try { size = fs.statSync(path.join(dir, "events.jsonl")).size; } catch { /* not there yet, or just deleted */ }
    state.eventsSeries.push({ tMs: now(), size });
    if (rootPid == null) {
      try { rootPid = Number(fs.readFileSync(path.join(dir, "pid"), "utf8").match(/^pid=(\d+)/m)?.[1]) || null; } catch { /* not yet */ }
    }
  }, 250);
}

function onSample(rows) {
  const t = now();
  state.samples++;
  // Never this watcher itself: with `--leaf node.exe` its own command line carries the marker.
  const leaves = rows.filter((r) => String(r.n).toLowerCase() === leaf && r.i !== process.pid);
  if (state.baselineCodex == null) state.baselineCodex = leaves.filter((r) => !norm(r.l).includes(marker)).map((r) => ({ pid: r.i, created: r.c }));

  // The scenario's leaf carries the marker AND the `-o <run dir>/last-message.json` argument.
  const marked = leaves.filter((r) => norm(r.l).includes(marker));
  const mine = marked.find((r) => runDirFrom(r.l)) ?? null;
  if (mine && !state.runDir) {
    state.moments.leafSeenMs = t;
    state.runDir = runDirFrom(mine.l);
    watchFiles();
    console.log(`[${(t / 1000).toFixed(0)} s] leaf ${mine.i} seen; run dir ${state.runDir}`);
  } else if (!mine && marked.length && !state.unparsedLogged) {
    state.unparsedLogged = true;
    console.log(`[${(t / 1000).toFixed(0)} s] a ${leaf} carries the marker but no -o …/last-message.json: ${marked[0].l}`);
  }

  const byPid = new Map(rows.map((r) => [r.i, r]));
  const add = (r, why) => { if (!members.has(key(r))) members.set(key(r), { pid: r.i, created: r.c, name: r.n, parentPid: r.p, commandLine: r.l ?? undefined, via: why, lastSeenMs: t }); };
  // Root from run.sh's pid file; until it can be read, the leaf's own ancestors (node, shell).
  if (rootPid != null && byPid.has(rootPid) && ![...members.values()].some((m) => m.via === "root")) { add(byPid.get(rootPid), "root"); state.rootSource = "pid file"; }
  if (mine) {
    add(mine, "leaf");
    let cur = mine;
    for (let hop = 0; hop < 3; hop++) {
      const parent = byPid.get(cur.p);
      if (!parent || !/^(node|sh|bash)\.exe$/i.test(parent.n) || (rootPid != null && cur.i === rootPid)) break;
      add(parent, "ancestor of leaf");
      if (parent.i === rootPid) break;
      cur = parent;
    }
    state.rootSource ??= "leaf ancestors";
  }
  // Descendants of any known member. A dead process cannot spawn, and Windows reuses pids
  // quickly (seen live: the dead root's pid went to an unrelated shell 20 s later), so a parent
  // must itself be in this sample, or have been in the previous one, and be older than the child.
  const present = new Set(rows.map(key));
  for (let grew = true; grew;) {
    grew = false;
    for (const r of rows) {
      if (members.has(key(r))) continue;
      const parent = [...members.values()].find((m) => m.pid === r.p && (!r.c || !m.created || r.c >= m.created)
        && (present.has(`${m.pid}@${m.created}`) || m.lastSeenMs >= prevSampleMs));
      if (parent) { add(r, `child of ${parent.pid}`); grew = true; }
    }
  }
  const alive = [];
  for (const r of rows) { const m = members.get(key(r)); if (m) { m.lastSeenMs = t; alive.push(r.i); } }

  const stop = state.moments.stopRequestedMs;
  if (stop != null) {
    if (state.moments.chainGoneMs == null && members.size && alive.length === 0) { state.moments.chainGoneMs = t; console.log(`[${(t / 1000).toFixed(0)} s] chain gone`); }
    if (state.aliveAt5 == null && t >= stop + 5_000) state.aliveAt5 = alive;
    if (state.aliveAt60 == null && t >= stop + 60_000) { state.aliveAt60 = alive; state.codexAt60 = leaves.map((r) => ({ pid: r.i, created: r.c })); }
    if (t >= stop + 65_000) return finish("65 s after the stop request");
  } else if (state.moments.lastMessageMs != null && t >= state.moments.lastMessageMs + 10_000) {
    if (members.size && alive.length === 0 && state.moments.chainGoneMs == null) state.moments.chainGoneMs = t;
    return finish("the run finished without a stop request");
  }
  prevSampleMs = t;
  if (t >= maxMs) finish("time limit");
}

function finish(why) {
  if (finished) return;
  finished = true;
  clearInterval(fileTimer);
  ps.kill();
  state.endedBecause = why;
  state.chain = [...members.values()];
  state.baselineCodex ??= [];
  state.aliveAt5 ??= [];
  state.aliveAt60 ??= [];
  state.codexAt60 ??= [];
  fs.writeFileSync(outFile, JSON.stringify(state, null, 1));
  console.log(`watch ended (${why}); ${state.samples} process samples, ${state.eventsSeries.length} file samples → ${outFile}`);
  process.exit(0);
}

let buf = "";
ps.stdout.setEncoding("utf8");
ps.stdout.on("data", (d) => {
  buf += d;
  for (let nl; (nl = buf.indexOf("\n")) >= 0;) {
    const line = buf.slice(0, nl).trim();
    buf = buf.slice(nl + 1);
    if (!line) continue;
    try { onSample(JSON.parse(line)); } catch (e) { console.error(`sample not parsed: ${e.message}`); }
  }
});
ps.on("exit", () => finish("the process sampler exited"));
process.on("SIGINT", () => finish("interrupted"));
console.log(`watching for ${leaf} with "${marker}" in its command line (scenario ${scenario})`);
