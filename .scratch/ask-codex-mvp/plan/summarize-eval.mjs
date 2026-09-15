// Summarize the newest N eval result dirs: per case score, cost, and every grader verdict.
// Usage: node summarize-eval.mjs [N=1]
import fs from "node:fs";
import path from "node:path";

const RES = "D:/work_data/project/skill/ask-codex/evals/results";
const n = Number(process.argv[2] || 1);
const dirs = fs.readdirSync(RES).filter((d) => fs.existsSync(path.join(RES, d, "aggregate-result.json"))).sort().slice(-n);

// Find grader verdict objects anywhere under a run object.
const verdicts = (o, out = []) => {
  if (Array.isArray(o)) o.forEach((x) => verdicts(x, out));
  else if (o && typeof o === "object") {
    if (typeof o.name === "string" && ("passed" in o || "pass" in o) && o !== null) out.push(o);
    else Object.values(o).forEach((x) => verdicts(x, out));
  }
  return out;
};

for (const d of dirs) {
  const a = JSON.parse(fs.readFileSync(path.join(RES, d, "aggregate-result.json"), "utf8"));
  console.log(`# ${d}  cost ${a.costUsd?.toFixed(3)}  partial ${a.partial}`);
  for (const c of a.cases) {
    for (const [arm, runs] of Object.entries(c.arms || {})) {
      runs.forEach((r, i) => {
        console.log(`CASE ${c.name} [${arm} #${i + 1}] score ${r.score} cost ${(r.costUsd ?? 0).toFixed(3)} turns ${r.turns} error ${r.error ?? "none"}`);
        for (const v of verdicts(r)) {
          const ok = v.passed ?? v.pass;
          const why = (v.reason || v.detail || v.message || v.explanation || "").toString().replace(/\s+/g, " ").slice(0, 220);
          console.log(`    ${ok ? "PASS" : "FAIL"} ${v.name} - ${why}`);
        }
      });
    }
  }
}
