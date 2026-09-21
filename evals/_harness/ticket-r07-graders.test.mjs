// Offline check for the conditional `temp-cleanup` grader (reliability ticket 07, Plan R07b S2):
//   node evals/_harness/ticket-r07-graders.test.mjs
// The grader is a not_contains regex on the trace: it must stay silent (the run passes) when no run
// directory was created and when every created directory is deleted, and it must find a directory
// (the run fails) when one was created and never deleted — including one of two in a parallel run.
// Real kept traces are the fixtures; the failing shapes are made by taking their `rm -rf` lines out.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const evidence = path.join(evals, "..", ".scratch", "ask-codex-reliability", "evidence");
let pass = 0, fail = 0;
const expect = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const cases = fs.readdirSync(evals).filter((c) => fs.existsSync(path.join(evals, c, "graders", "temp-cleanup.md")));
const bodies = new Set(cases.map((c) => fs.readFileSync(path.join(evals, c, "graders", "temp-cleanup.md"), "utf8").replace(/\r\n/g, "\n")));
expect(cases.length === 49, `49 cases carry temp-cleanup (found ${cases.length})`);
expect(bodies.size === 1, "the grader is byte-identical in every case");
const body = [...bodies][0];
expect(/^type: regex$/m.test(body) && /^match: not_contains$/m.test(body) && /^target: trace$/m.test(body), "a not_contains regex on the trace");
const leak = new RegExp(body.match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"));

const trace = (...p) => fs.readFileSync(path.join(evidence, ...p), "utf8");
const RM = /rm\s+-rf\s+(?:--\s+)?'[^']*\/ask-codex\//;
const withoutRm = (t) => t.split("\n").filter((l) => !RM.test(l)).join("\n");
const dirs = (t) => [...new Set([...t.matchAll(/\/ask-codex\/(run\.(?!XXXXXX)[A-Za-z0-9]{6})/g)].map((m) => m[1]))];

// 1. No allocation: early stops at a confirmation (the shape the old tool_used grader failed).
for (const f of ["pre-confirm-mismatch-hgaCzQ.jsonl", "project-layer-aborts-01-FypmJt.jsonl"]) {
  const t = trace("07-traces", f);
  expect(dirs(t).length === 0 && !leak.test(t), `${f}: no run directory created → passes`);
}

// 2. Allocate and delete: a plain consultation, in the harness's own trace format (S2 probe run).
const plain = trace("07b-traces", "manual-with-question-claude-eval-cErdTe.jsonl");
expect(dirs(plain).length === 1 && !leak.test(plain), "plain consultation: created and deleted → passes");
// 3. Allocate, never delete.
expect(leak.test(withoutRm(plain)), "plain consultation without its rm line → fails");
expect(leak.exec(withoutRm(plain))?.[1] === dirs(plain)[0], "  … and names the directory that was left");

// 4. Parallel: two directories.
const par = trace("03-parallel-shared-timer-CrmnfO-trace.jsonl");
const [d1, d2] = dirs(par);
expect(dirs(par).length === 2 && !leak.test(par), "parallel run: both directories deleted → passes");
const oneLeft = par.split("\n").filter((l) => !(RM.test(l) && l.includes(d2) && !l.includes(d1))).join("\n")
  .replace(new RegExp(`\\s*;?\\s*rm\\s+-rf\\s+(?:--\\s+)?'[^']*/ask-codex/${d2.replace(".", "\\.")}'`, "g"), "");
expect(leak.exec(oneLeft)?.[1] === d2, "parallel run with only the first directory deleted → fails, naming the second");

// 5. Stopped run: `cat -- '<tmp>/stop-report'; rm -rf -- '<tmp>'`.
const stopped = trace("03-timeout-stalled-stop-1QD3n2-trace.jsonl");
expect(/cat -- '[^']*\/stop-report'; rm -rf -- '/.test(stopped) && !leak.test(stopped), "stopped run, cleanup line with stop-report → passes");
expect(leak.test(withoutRm(stopped)), "stopped run without the cleanup line → fails");

// 6. Synthetic shapes, written the way the trace stores them (JSON lines: quotes and newlines escaped).
const use = (command) => JSON.stringify({ type: "assistant", message: { content: [{ type: "tool_use", name: "Bash", input: { command } }] } });
const result = (stdout) => JSON.stringify({ type: "user", message: { content: [{ type: "tool_result", content: stdout }] } });
const P = "/tmp/x/ask-codex";
const mk = use(`mkdir -p '${P}' && mktemp -d '${P}/run.XXXXXX'`);
expect(!leak.test(mk), "the mktemp template alone is not a directory");
expect(!leak.test([mk, result(`${P}/run.Ab12Cd\n`), use(`rm -rf -- '${P}/run.Ab12Cd'`)].join("\n")), "output with a trailing newline, then rm → passes");
expect(!leak.test([mk, result(`${P}/run.Ab12Cd`), use(`rm -rf '${P}/run.Ab12Cd'`)].join("\n")), "rm without `--` → passes");
expect(!leak.test([mk, result(`${P}/run.Ab12Cd\n${P}/run.Zz99Yy`), use(`rm -rf -- '${P}/run.Ab12Cd' '${P}/run.Zz99Yy'`)].join("\n")), "one rm naming both directories → passes");
expect(leak.test([mk, result(`${P}/run.Ab12Cd\n${P}/run.Zz99Yy`), use(`rm -rf -- '${P}/run.Ab12Cd'`)].join("\n")), "two created, one deleted → fails");
expect(leak.test([use(`rm -rf -- '${P}/run.Ab12Cd'`), mk, result(`${P}/run.Ab12Cd`)].join("\n")), "an rm BEFORE the directory was created does not count");
expect(leak.test([mk, result(`${P}/run.Ab12Cd`), use(`rm -rf -- '${P}/run.Qq11Ww'`)].join("\n")), "deleting another directory does not count");
expect(leak.test([mk, result(`${P}/run.Ab12Cd`), use(`ls '${P}/run.Ab12Cd'`)].join("\n")), "a command that only mentions the directory does not count");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
