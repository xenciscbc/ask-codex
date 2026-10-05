// Compare per-grader failure counts between two fingerprinted run logs (discuss-skill regression check).
//   node .scratch/discuss-skill/compare-graders.mjs <candidate-log> <baseline-log> [case ...]
// A log section starts with "=== <case> x<runs>"; each failed grader of a run is a line "    ✗ <grader> (weight …".
// Prints, per case and grader, failures on candidate vs baseline, and flags a grader that fails more often
// on the candidate. Lines of a run that errored (timed out) are counted too; such runs are listed separately.
import { readFileSync } from "node:fs";

function parse(file) {
  const cases = {};
  let current = null;
  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    const head = line.match(/^=== (\S+) x(\d+)$/);
    if (head) { current = cases[head[1]] = { runs: Number(head[2]), fails: {}, errors: 0 }; continue; }
    if (!current) continue;
    if (/run \d+\/\d+: score .*error:/.test(line)) current.errors++;
    const fail = line.match(/^\s+✗ (\S+) \(weight/);
    if (fail) current.fails[fail[1]] = (current.fails[fail[1]] || 0) + 1;
  }
  return cases;
}

const [candFile, baseFile, ...only] = process.argv.slice(2);
const cand = parse(candFile), base = parse(baseFile);
const names = only.length ? only : Object.keys(base).filter((c) => c in cand);
let worse = 0;
for (const c of names) {
  const a = cand[c], b = base[c];
  if (!a || !b) { console.log(`${c}: missing in ${!a ? "candidate" : "baseline"}`); continue; }
  console.log(`${c}  (candidate ${a.runs} runs, ${a.errors} errored; baseline ${b.runs} runs, ${b.errors} errored)`);
  const graders = [...new Set([...Object.keys(a.fails), ...Object.keys(b.fails)])].sort();
  if (!graders.length) console.log("  no failures on either");
  for (const g of graders) {
    const fa = a.fails[g] || 0, fb = b.fails[g] || 0;
    const flag = fa > fb ? "  <-- fails more on candidate" : "";
    if (fa > fb) worse++;
    console.log(`  ${g}: candidate ${fa}/${a.runs}, baseline ${fb}/${b.runs}${flag}`);
  }
}
console.log(`graders failing more often on the candidate: ${worse}`);
