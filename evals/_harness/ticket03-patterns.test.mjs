// Offline check for the ticket-03 cases (run before any paid eval run):
//   node evals/_harness/ticket03-patterns.test.mjs
// 1. Token readings: the reference model-token rule reads every ticket-03 prompt as the slice expects.
// 2. Argv graders: each accepts the expected slug/effort and rejects its neighbour.
// 3. Safety: every ticket-03 scaffold refuses to seed a Codex home outside the eval sandbox.
// 4. No hardcoded alias table in the skill.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readRequest } from "./model-token-rule.mjs";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const evals = path.join(repo, "evals");
let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const cases = fs.readdirSync(evals).filter((d) => {
  const f = path.join(evals, d, "case.yaml");
  return d !== "codex-home-probe" && fs.existsSync(f) && /tags: \[ticket-03\]/.test(fs.readFileSync(f, "utf8"));
});
const promptOf = (c) => fs.readFileSync(path.join(evals, c, "prompt.md"), "utf8").split(/\n---\n/)[1].trim().replace(/^\/ask-codex:ask\s*/, "");
const scaffoldOf = (c) => fs.readFileSync(path.join(evals, c, "scaffold.sh"), "utf8");
const listed = (c) => {
  const m = scaffoldOf(c).match(/models_cache\.json" <<'EOF'\n([\s\S]*?)EOF\n/);
  return m ? JSON.parse(m[1]).models.filter((x) => x.visibility === "list").map((x) => x.slug) : [];
};

// 1. Token readings
const READ = {
  "alias-sol": (r) => r.kind === "model" && r.matches.join() === "gpt-5.6-sol" && !r.effort,
  "alias-astra": (r) => r.matches?.join() === "gpt-6-astra",
  "alias-sol-low": (r) => r.matches?.join() === "gpt-5.6-sol" && r.effort === "low",
  "alias-ambiguous": (r) => r.matches?.length === 3,
  "alias-unknown": (r) => r.kind === "model" && !r.invalid && r.matches.length === 0,
  "alias-metachar": (r) => r.kind === "model" && r.invalid,
  "effort-unsupported": (r) => r.matches?.join() === "gpt-5.5" && r.effort === "max",
  "default-model-config": (r) => r.kind === "none",
  "session-override-persists": (r) => r.kind === "none",
  "override-restated-no-prompt": (r) => r.matches?.join() === "gpt-6-astra",
};
for (const c of cases) {
  if (!READ[c]) { check(false, `no expected reading for ${c}`); continue; }
  check(READ[c](readRequest(promptOf(c), listed(c))), `token reading ${c}`);
}
check(readRequest("Why does fetchUser in src/user.js return an empty object when the API times out?", []).kind === "none", "regression prompt without a cache");

// 2. Argv graders
const graderOf = (c, g) => {
  const t = fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
  return { re: new RegExp(t.match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'")), match: (t.match(/^match: (\S+)$/m) || [, "contains"])[1] };
};
const argvSample = (slug, effort) => JSON.stringify(["exec", "-s", "read-only", "--ephemeral", ...(slug ? ["-m", slug] : []), "-c", `model_reasoning_effort="${effort}"`, "--disable", "apps"], null, 2);
const expectArgv = (c, g, slug, effort, want, label) => {
  const { re } = graderOf(c, g);
  check(re.test(argvSample(slug, effort)) === want, `${c}/${g} ${label}`);
};
const pairs = [
  ["alias-sol", "model-sol", "gpt-5.6-sol", "gpt-5.6-terra"], ["alias-astra", "model-astra", "gpt-6-astra", "gpt-5.6-sol"],
  ["effort-unsupported", "model-55", "gpt-5.5", "gpt-5.6-sol"], ["default-model-config", "model-terra", "gpt-5.6-terra", "gpt-5.6-luna"],
  ["session-override-persists", "model-astra", "gpt-6-astra", "gpt-5.6-terra"], ["override-restated-no-prompt", "model-astra", "gpt-6-astra", "gpt-5.6-terra"],
];
for (const [c, g, good, bad] of pairs) {
  expectArgv(c, g, good, "medium", true, `accepts ${good}`);
  expectArgv(c, g, bad, "medium", false, `rejects ${bad}`);
}
for (const [c, g, good, bad] of [["alias-sol", "effort-high", "high", "medium"], ["alias-astra", "effort-medium", "medium", "high"], ["alias-sol-low", "effort-medium", "medium", "low"],
  ["effort-unsupported", "effort-xhigh", "xhigh", "max"], ["default-model-config", "effort-medium", "medium", "low"], ["session-override-persists", "effort-medium", "medium", "high"]]) {
  expectArgv(c, g, "gpt-5.6-sol", good, true, `accepts effort ${good}`);
  expectArgv(c, g, "gpt-5.6-sol", bad, false, `rejects effort ${bad}`);
}
// not_contains graders: must fire (match) on the forbidden effort and stay quiet otherwise.
for (const [c, g, forbidden, ok] of [["alias-sol-low", "no-effort-low", "low", "medium"], ["effort-unsupported", "no-effort-max", "max", "xhigh"], ["default-model-config", "no-effort-low", "low", "medium"]]) {
  const { re, match } = graderOf(c, g);
  check(match === "not_contains", `${c}/${g} is not_contains`);
  check(re.test(argvSample("gpt-5.6-sol", forbidden)), `${c}/${g} matches ${forbidden}`);
  check(!re.test(argvSample("gpt-5.6-sol", ok)), `${c}/${g} ignores ${ok}`);
}

// 3. Scaffold guard: the refusal comes before any write to $HOME.
const GUARD = 'case "$HOME" in *claude-eval*) ;; *) echo "refusing to seed a Codex home outside the eval sandbox: HOME=$HOME" >&2; exit 1;; esac';
for (const c of [...cases, "codex-home-probe"]) {
  const s = scaffoldOf(c);
  const g = s.indexOf(GUARD), w = s.indexOf('"$HOME/');
  check(g >= 0 && w > g, `${c} scaffold guards $HOME before writing it`);
}

// 4. No hardcoded alias table (alias -> slug mappings) in the skill.
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
for (const f of walk(path.join(repo, "skills"))) {
  const t = fs.readFileSync(f, "utf8");
  const hit = t.match(/\b(sol|astra|terra|luna)\b[`'"]?\s*(→|->|=>|=|:)\s*[`'"]?gpt-/i);
  check(!hit, `no alias table in ${path.relative(repo, f)}${hit ? ` (${hit[0]})` : ""}`);
}

console.log(`${pass} passed, ${fail} failed (${cases.length} ticket-03 cases)`);
process.exit(fail ? 1 : 0);
