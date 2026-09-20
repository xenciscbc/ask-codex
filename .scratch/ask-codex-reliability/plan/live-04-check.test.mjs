// Offline check for the slice-04 live checker:
//   node .scratch/ask-codex-reliability/plan/live-04-check.test.mjs
// One synthetic watch file per exit code of live-04-check.mjs and per P1 shape, so every
// disposition in slice-04.md is reachable and distinguishable without spending a Codex call.
import { judge } from "./live-04-check.mjs";

let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const LINE = "Consultation stopped: interval 1 minutes (override); elapsed 1:14; last event turn.started 1:13 ago; offered: wait another 1 minutes / stop (recommended: stop); process tree ended";
const reply = (line = LINE) => `--- assistant text 1 ---\nSending the question to Codex.\n[tool: Bash]\n--- assistant text 2 ---\n${line}\n[tool: TaskStop]\n--- assistant text 3 ---\n${line}\n\nThe consultation was stopped; nothing here comes from Codex.\n`;

// Times in ms from the watcher's start. Stop requested at 70 000; the chain is gone one process
// sample later; stop.sh reports after its own 5 s window; the skill deletes the run dir ~3 s later.
const STOP = 70_000;
const series = (from, to, size, step = 250) => {
  const out = [];
  for (let t = from; t <= to; t += step) out.push({ tMs: t, size });
  return out;
};
const good = () => ({
  scenario: "T",
  runDir: "R:/Temp/ask-codex/run.AbC123",
  baselineCodex: [{ pid: 900, created: "2026-09-20T01:00:00.000Z" }],
  chain: [
    { pid: 1100, created: "2026-09-20T09:00:00.000Z", name: "sh.exe", lastSeenMs: 70_400 },
    { pid: 1101, created: "2026-09-20T09:00:00.300Z", name: "node.exe", lastSeenMs: 70_400 },
    { pid: 1102, created: "2026-09-20T09:00:00.900Z", name: "codex.exe", lastSeenMs: 70_400 },
  ],
  moments: { stopRequestedMs: STOP, chainGoneMs: 71_300, reportedMs: 77_000, lastMessageMs: null, runDirGoneMs: 80_000 },
  aliveAt5: [],
  aliveAt60: [],
  codexAt60: [{ pid: 900, created: "2026-09-20T01:00:00.000Z" }],
  eventsSeries: [...series(10_000, STOP, 2092, 1000), ...series(STOP + 250, 79_750, 2092)],
});
const expect = (label, mutate, exit, text = reply()) => {
  const w = good();
  mutate(w);
  const r = judge(w, text);
  check(r.exit === exit, `${label}: exit ${r.exit}, expected ${exit} — ${r.reasons.join("; ")}`);
};

expect("clean stop", () => {}, 0);
expect("bold fixed words in the reply", () => {}, 0, reply(LINE.replace("Consultation stopped:", "**Consultation stopped:**")));
expect("event flushed between the stop request and chain gone", (w) => {
  w.eventsSeries = [...series(10_000, STOP, 2092, 1000), ...series(STOP + 250, 71_250, 2092), ...series(71_300, 79_750, 2710)];
  w.eventsSeries.find((s) => s.tMs === STOP + 750).size = 2710;
}, 0);
expect("alive at +5 s but gone before reported", (w) => {
  w.chain.forEach((m) => { m.lastSeenMs = 75_600; });
  w.moments.chainGoneMs = 76_500;
  w.aliveAt5 = [1102];
}, 0);
expect("pid reused by another process (different creation time) at +60 s", (w) => {
  w.codexAt60.push({ pid: 900, created: "2026-09-20T01:00:00.000Z" });
  w.aliveAt60 = []; // the watcher compares pid + created, so a reused 1102 is not listed
}, 0);

// Seen live (scenario H, first run): the dead root's pid was reused by an unrelated shell 20 s
// after the chain was gone, and its `sleep.exe` was adopted as a "child". A dead process cannot
// spawn: a member created after its parent member was last seen is not part of the chain.
const T0 = "2026-09-20T08:58:50.000Z"; // watcher start; the chain above was created ~70 s later
expect("'child' created after its parent was last seen (parent pid reused) → excluded", (w) => {
  w.startedAt = T0;
  w.chain.push({ pid: 3499, created: "2026-09-20T09:00:21.840Z", name: "sleep.exe", parentPid: 1100, via: "child of 1100", lastSeenMs: 131_000 });
  w.aliveAt60 = [3499];
}, 0);
expect("child created while its parent was alive, and it outlives the report → P1", (w) => {
  w.startedAt = T0;
  w.chain.push({ pid: 3500, created: "2026-09-20T08:59:40.000Z", name: "powershell.exe", parentPid: 1102, via: "child of 1102", lastSeenMs: 131_000 });
  w.aliveAt60 = [3500];
}, 10);

// exit 3 — not a stop scenario
expect("run finished, no stop request", (w) => {
  w.moments = { stopRequestedMs: null, chainGoneMs: 40_000, reportedMs: null, lastMessageMs: 39_000, runDirGoneMs: 45_000 };
}, 3);
expect("last-message within 2 s of the stop request (race)", (w) => { w.moments.lastMessageMs = STOP + 1500; }, 3);

// exit 4 — watcher never identified the run
expect("no run directory", (w) => { w.runDir = null; w.chain = []; }, 4);
expect("chain lacks node.exe", (w) => { w.chain = w.chain.filter((m) => m.name !== "node.exe"); }, 4);
expect("chain lacks a shell", (w) => { w.chain = w.chain.filter((m) => m.name !== "sh.exe"); }, 4);
expect("no stop request and no last-message", (w) => {
  w.moments = { stopRequestedMs: null, chainGoneMs: null, reportedMs: null, lastMessageMs: null, runDirGoneMs: null };
}, 4);

// exit 5 — quiet window too small
expect("too few quiet-window samples", (w) => {
  w.eventsSeries = [...series(10_000, STOP, 2092, 1000), ...series(71_300, 72_800, 2092)];
}, 5);
expect("enough samples but under 2 s", (w) => {
  w.eventsSeries = [...series(10_000, STOP, 2092, 1000), ...series(71_300, 73_000, 2092, 100).slice(0, 12)];
}, 5);

// exit 6 — processes fine, reply lacks the line
expect("reply has no Consultation stopped line", () => {}, 6, reply("I stopped the consultation because it looked stalled."));
expect("reply line lacks a field", () => {}, 6, reply(LINE.replace("elapsed 1:14; ", "")));

// exit 10 — P1 shapes
expect("member outlives reported", (w) => { w.chain[2].lastSeenMs = 78_000; w.moments.chainGoneMs = 79_000; }, 10);
expect("member gone before reported but after the 15 s bound", (w) => {
  w.chain[2].lastSeenMs = 86_000; w.moments.chainGoneMs = 87_000; w.moments.reportedMs = 93_000; w.moments.runDirGoneMs = 97_000;
  w.eventsSeries = [...series(10_000, STOP, 2092, 1000), ...series(87_000, 96_750, 2092)];
}, 10);
expect("member alive at +60 s", (w) => { w.aliveAt60 = [1102]; w.chain[2].lastSeenMs = 135_000; }, 10);
expect("chain never seen gone", (w) => { w.moments.chainGoneMs = null; w.aliveAt60 = [1102]; }, 10);
expect("events.jsonl grows inside the quiet window", (w) => { w.eventsSeries.at(-3).size = 2710; w.eventsSeries.at(-2).size = 2710; w.eventsSeries.at(-1).size = 2710; }, 10);
expect("codex.exe outside the baseline at +60 s", (w) => { w.codexAt60.push({ pid: 2222, created: "2026-09-20T09:00:30.000Z" }); }, 10);
expect("last-message more than 2 s after the stop request", (w) => { w.moments.lastMessageMs = STOP + 9000; }, 10);
expect("reply says NOT confirmed", () => {}, 10, reply(LINE.replace("process tree ended", "process tree NOT confirmed — pids 1102")));
expect("no reported moment (stop.sh never wrote its report)", (w) => { w.moments.reportedMs = null; }, 10);

// P1 wins over the softer codes.
expect("P1 plus missing line → 10", (w) => { w.aliveAt60 = [1102]; w.chain[2].lastSeenMs = 135_000; }, 10, reply("stopped."));

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
