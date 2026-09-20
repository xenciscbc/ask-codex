// Slice 04: judge one live stop scenario from the watcher's JSON and the saved reply text.
//   node .scratch/ask-codex-reliability/plan/live-04-check.mjs <watch.json> <reply.md>
// Exit codes (dispositions in plan/slice-04.md, Outcome 1):
//   0 pass · 3 not a stop scenario (retry) · 4 run/chain never identified (tooling)
//   5 quiet window too small (inconclusive) · 6 reply lacks the stop line (P2) · 10 P1
// The stop-line regex is READ FROM THE SHIPPED GRADER (evals/timeout-stalled-stop/graders/
// stopped-line.md), never written here, so the live check and the eval suite judge one shape.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..", "..");

const KILL_BOUND_MS = 15_000; // stop.sh waits up to RESULT_WAIT_S = 10 s for run.sh's answer
const RACE_MS = 2_000;
const REUSE_SLACK_MS = 2_000;
const QUIET_MIN_SAMPLES = 8;
const QUIET_MIN_MS = 2_000;

function stoppedLineRe() {
  const t = fs.readFileSync(path.join(root, "evals", "timeout-stalled-stop", "graders", "stopped-line.md"), "utf8");
  const m = t.match(/^pattern: '((?:[^']|'')*)'$/m);
  if (!m) throw new Error("cannot read the pattern from stopped-line.md");
  return new RegExp(m[1].replace(/''/g, "'"));
}

export function judge(w, replyText) {
  const m = w.moments ?? {};
  const notes = [];
  // A dead process cannot spawn. A "child" created after its parent member was last seen got
  // there through a reused parent pid (seen live: the dead root's pid went to an unrelated
  // shell 20 s later) — it is not part of the chain. Slack: two process samples.
  const t0 = Date.parse(w.startedAt ?? "");
  const excluded = new Set();
  for (const c of w.chain ?? []) {
    const parent = (w.chain ?? []).find((p) => p.pid === c.parentPid && p !== c && /^child of /.test(c.via ?? ""));
    const bornMs = Date.parse(c.created ?? "") - t0;
    if (parent && Number.isFinite(bornMs) && bornMs > parent.lastSeenMs + REUSE_SLACK_MS) {
      excluded.add(c.pid);
      notes.push(`excluded ${c.name} ${c.pid}: created ${((bornMs - parent.lastSeenMs) / 1000).toFixed(1)} s after its recorded parent ${parent.name} ${parent.pid} was last seen (parent pid reused)`);
    }
  }
  const chain = (w.chain ?? []).filter((c) => !excluded.has(c.pid));
  const aliveAt60 = (w.aliveAt60 ?? []).filter((p) => !excluded.has(p));
  const aliveAt5 = (w.aliveAt5 ?? []).filter((p) => !excluded.has(p));
  const names = new Set(chain.map((c) => String(c.name).toLowerCase()));
  const done = (exit, reasons) => ({ exit, reasons, notes });

  // 4 — nothing to judge.
  const hasChain = (names.has("sh.exe") || names.has("bash.exe")) && names.has("node.exe") && names.has("codex.exe");
  if (!w.runDir || !hasChain) return done(4, [`run directory or sh/bash → node → codex.exe chain not identified (run dir ${w.runDir ?? "none"}, chain ${[...names].join(", ") || "empty"})`]);
  if (m.stopRequestedMs == null && m.lastMessageMs == null) return done(4, ["neither a stop request nor a finished run was observed"]);

  // 3 — the run completed; this was not a stop.
  if (m.stopRequestedMs == null) return done(3, ["the run finished before any stop request"]);
  if (m.lastMessageMs != null && m.lastMessageMs - m.stopRequestedMs <= RACE_MS) return done(3, ["last-message.json appeared within 2 s of the stop request: the run was completing"]);

  // 10 — P1 shapes.
  const p1 = [];
  if (m.lastMessageMs != null) p1.push(`last-message.json appeared ${((m.lastMessageMs - m.stopRequestedMs) / 1000).toFixed(1)} s after the stop request`);
  if (m.reportedMs == null) p1.push("stop-report never appeared, so 'gone before stop.sh reported' cannot be shown");
  if (m.chainGoneMs == null) p1.push("the chain was never seen gone");
  for (const c of chain) {
    if (m.reportedMs != null && c.lastSeenMs > m.reportedMs) p1.push(`${c.name} ${c.pid} was still alive after stop.sh reported`);
    if (c.lastSeenMs > m.stopRequestedMs + KILL_BOUND_MS) p1.push(`${c.name} ${c.pid} was alive more than 15 s after the stop request`);
  }
  if (aliveAt60.length) p1.push(`chain members alive at +60 s: ${aliveAt60.join(", ")}`);
  const base = new Set((w.baselineCodex ?? []).map((p) => `${p.pid}@${p.created}`));
  const strangers = (w.codexAt60 ?? []).filter((p) => !base.has(`${p.pid}@${p.created}`));
  if (strangers.length) p1.push(`codex.exe outside the baseline at +60 s: ${strangers.map((p) => p.pid).join(", ")}`);

  const quiet = m.chainGoneMs == null ? [] : (w.eventsSeries ?? []).filter((s) => s.tMs >= m.chainGoneMs && s.size != null);
  const quietMs = quiet.length ? quiet.at(-1).tMs - quiet[0].tMs : 0;
  if (quiet.length && new Set(quiet.map((s) => s.size)).size > 1) p1.push(`events.jsonl changed inside the quiet window (${quiet[0].size} → ${quiet.at(-1).size} bytes)`);
  if (/Consultation stopped:[\s\S]{0,400}?process tree NOT confirmed/.test(replyText)) p1.push("the reply's stop line ends 'process tree NOT confirmed'");
  if (p1.length) return done(10, p1);

  // Informational.
  const killMs = m.chainGoneMs - m.stopRequestedMs;
  notes.push(`kill duration (stop request → chain gone) ${(killMs / 1000).toFixed(1)} s`);
  notes.push(`quiet window ${(quietMs / 1000).toFixed(1)} s, ${quiet.length} samples, ${quiet[0]?.size ?? "?"} bytes throughout`);
  if (aliveAt5.length) notes.push(`alive at +5 s, gone before stop.sh reported: ${aliveAt5.join(", ")}`);
  const before = (w.eventsSeries ?? []).filter((s) => s.tMs <= m.stopRequestedMs && s.size != null).at(-1);
  if (before && quiet.length && before.size !== quiet[0].size) notes.push(`one flush between the stop request and chain gone (${before.size} → ${quiet[0].size} bytes)`);

  // 5 — inconclusive on growth only.
  if (quiet.length < QUIET_MIN_SAMPLES || quietMs < QUIET_MIN_MS) return done(5, [`quiet window too small: ${quiet.length} samples over ${(quietMs / 1000).toFixed(1)} s (needs ≥ ${QUIET_MIN_SAMPLES} over ≥ 2 s)`]);

  // 6 — processes fine, reply lacks the line.
  if (!stoppedLineRe().test(replyText)) return done(6, ["the reply has no complete 'Consultation stopped: … process tree ended' line"]);

  return done(0, ["all checks passed"]);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [watchFile, replyFile] = process.argv.slice(2);
  if (!watchFile || !replyFile) { console.error("usage: live-04-check.mjs <watch.json> <reply.md>"); process.exit(2); }
  const r = judge(JSON.parse(fs.readFileSync(watchFile, "utf8")), fs.readFileSync(replyFile, "utf8"));
  for (const x of r.reasons) console.log(`${r.exit === 0 ? "PASS" : "FAIL"} ${x}`);
  for (const x of r.notes) console.log(`note ${x}`);
  console.log(`exit ${r.exit}`);
  process.exit(r.exit);
}
