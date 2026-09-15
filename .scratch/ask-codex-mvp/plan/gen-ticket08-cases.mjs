// Generates the ticket-08 eval cases (slice-08 revision 2, READY). Codex-home seeding as in ticket 03
// (HOME guard); workspace as in ticket 01 so the stub replies match.
// Usage: node gen-ticket08-cases.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const EVALS = "D:/work_data/project/skill/ask-codex/evals";
const FIX = path.join(path.dirname(fileURLToPath(import.meta.url)), "t03-fixture");
const copy = (from) => fs.readFileSync(path.join(EVALS, from), "utf8");
const CACHE = fs.readFileSync(path.join(FIX, "models_cache.json"), "utf8");
const CONFIG = fs.readFileSync(path.join(FIX, "config.toml"), "utf8");
const T01 = copy("manual-with-question/scaffold.sh");
const heredoc = (file) => T01.split(`cat > ${file} <<'EOF'\n`)[1].split("EOF\n")[0];

const G = {
  skillFired: copy("diagnosis-blind/graders/skill-fired.md"),
  oneExec: copy("diagnosis-blind/graders/one-codex-exec.md"),
  noViolations: copy("diagnosis-blind/graders/no-violations.md"),
  noBareCd: copy("diagnosis-blind/graders/no-bare-cd.md"),
  tempCleanup: copy("diagnosis-blind/graders/temp-cleanup.md"),
  noCodexAny: copy("manual-without-question-nothing-to-infer/graders/no-codex-call.md"),
  noExecSentinel: copy("manual-without-question-nothing-to-infer/graders/no-exec-sentinel.md"),
  allDisabled: copy("manual-with-question/graders/all-servers-disabled.md"),
};
G.twoExec = G.oneExec.replace("min: 1\nmax: 1", "min: 2\nmax: 2");
if (G.twoExec === G.oneExec) throw new Error("could not derive the two-exec grader");
const DISABLE_PATTERN = G.allDisabled.match(/^pattern: '((?:[^']|'')*)'$/m)[1];

export const GUARD = `case "$HOME" in *claude-eval*) ;; *) echo "refusing to seed a Codex home outside the eval sandbox: HOME=$HOME" >&2; exit 1;; esac`;
const q = (p) => p.replace(/'/g, "''");
const rx = (p, match) => `---\ntype: regex\npattern: '${q(p)}'\n${match ? `match: ${match}\n` : ""}---\n`;
const onFile = (file, p, match) => `---\ntype: regex\npattern: '${q(p)}'\n${match ? `match: ${match}\n` : ""}target:\n  source: file\n  path: ${file}\n---\n`;
const llm = (t) => `---\ntype: llm\n---\n\n${t.trim()}\n`;
const toolUsed = (tool, inputMatch, min, max) => `---\ntype: tool_used\ntool: ${tool}\n${inputMatch ? `input_match: '${q(inputMatch)}'\n` : ""}min: ${min}\n${max !== undefined ? `max: ${max}\n` : ""}---\n`;

const SLUGS = { astra: "gpt-6-astra", sol: "gpt-5.6-sol" };
const esc = (s) => s.replace(/\./g, "\\.");
const EXEC_BG = String.raw`(?=.*codex(?:\\"|')?\s+exec\b)(?=.*"run_in_background"\s*:\s*true)`;
const perRun = (slugs) => {
  const out = { "no-violations": G.noViolations, "two-temp-dirs": toolUsed("Bash", String.raw`mktemp -d`, 2), "two-background-runs": toolUsed("Bash", EXEC_BG, 2) };
  for (const s of slugs) {
    const f = `.stub/exec-argv.${s}.json`;
    out[`${s}-disable-set`] = `---\ntype: regex\npattern: '${DISABLE_PATTERN}'\nmatch: "count:5"\ntarget:\n  source: file\n  path: ${f}\n---\n`;
    out[`${s}-read-only`] = onFile(f, String.raw`"-s",\s*"read-only"`);
    out[`${s}-disable-apps`] = onFile(f, String.raw`"--disable",\s*"apps"`);
  }
  return out;
};

const claim = (id, statement, kind = "inference", confidence = "medium", evidence = []) => ({ id, statement, kind, confidence, evidence, followup_status: null });
const SHARED = "fetchUser catches TimeoutError and returns an empty object instead of rethrowing.";
export const REPLIES = {
  astra: { summary: "Timeouts are swallowed into an empty object; a circuit breaker would keep the page honest.", claims: [
    claim("C1", SHARED, "fact", "high", ["src/user.js:7"]),
    claim("C2", "A circuit breaker around api.get would stop repeated slow calls from piling up.", "inference", "low"),
    claim("C3", "Raising the timeout to 10s would fix the user-not-found reports.", "inference", "medium")], open_questions: [] },
  sol: { summary: "Timeouts are swallowed into an empty object; cancelling with AbortController would surface them.", claims: [
    claim("C1", SHARED, "fact", "high", ["src/user.js:7"]),
    claim("C2", "An AbortController signal would let callers tell a timeout from a missing user.", "inference", "medium"),
    claim("C3", "Raising the timeout would only hide the symptom; the error handling is the real problem.", "inference", "high")], open_questions: [] },
};
const Q = "Why does fetchUser in src/user.js return an empty object when the API times out?";
const REFUSE = "Parallel consultation takes at most two different models";

const merged = {
  "exec-twice": G.twoExec,
  "astra-model": onFile(`.stub/exec-argv.${SLUGS.astra}.json`, String.raw`"-m",\s*"gpt-6-astra"`),
  "astra-effort": onFile(`.stub/exec-argv.${SLUGS.astra}.json`, String.raw`model_reasoning_effort=\\"medium\\"`),
  "sol-model": onFile(`.stub/exec-argv.${SLUGS.sol}.json`, String.raw`"-m",\s*"gpt-5\.6-sol"`),
  "sol-effort": onFile(`.stub/exec-argv.${SLUGS.sol}.json`, String.raw`model_reasoning_effort=\\"high\\"`),
  "astra-stdin-question": onFile(`.stub/exec-stdin.${SLUGS.astra}.txt`, "fetchUser"),
  "sol-stdin-question": onFile(`.stub/exec-stdin.${SLUGS.sol}.txt`, "fetchUser"),
  "astra-stdin-no-sol": onFile(`.stub/exec-stdin.${SLUGS.astra}.txt`, "AbortController", "not_contains"),
  "sol-stdin-no-astra": onFile(`.stub/exec-stdin.${SLUGS.sol}.txt`, "[Cc]ircuit breaker", "not_contains"),
};
const base = (slugs) => ({ "skill-fired": G.skillFired, "no-bare-cd": G.noBareCd, "temp-cleanup": G.tempCleanup, ...perRun(slugs) });

export const CASES = [
  { name: "parallel-two-models", prompt: `/ask-codex:ask astra, sol ${Q}`, scenario: { exec: { by_model: { [SLUGS.astra]: { reply: REPLIES.astra }, [SLUGS.sol]: { reply: REPLIES.sol } } } },
    graders: { ...base([SLUGS.astra, SLUGS.sol]), ...merged,
      "h-consensus": rx("Consensus"), "h-solo": rx("Solo claims"), "h-divergences": rx("Divergences"),
      "tag-astra": rx(String.raw`\[gpt-6-astra\]`), "tag-sol": rx(String.raw`\[gpt-5\.6-sol\]`), "adopted": rx("Adopted:"), "merged-llm": llm(`
Two models answered the same question. Both said fetchUser catches TimeoutError and returns an empty object (consensus). gpt-6-astra alone suggested a circuit breaker; gpt-5.6-sol alone suggested an AbortController signal (solo claims). They disagree on whether raising the timeout would fix the problem (divergence).
PASS if the final response groups the claims into consensus, solo claims and divergences with the right model tags, gives each claim a disposition, and for the divergence says which side it adopts and why.
FAIL if a group is wrong or missing, a claim is attributed to the wrong model, or the divergence has no adoption rationale.`) } },
  { name: "parallel-three-refused", prompt: `/ask-codex:ask astra, sol, terra ${Q}`, scenario: {},
    graders: { "no-bare-cd": G.noBareCd, "no-codex-call": G.noCodexAny, "no-exec-sentinel": G.noExecSentinel, "refusal": rx(REFUSE) } },
  { name: "parallel-duplicate-refused", prompt: `/ask-codex:ask sol, 5.6-sol ${Q}`, scenario: {},
    graders: { "no-bare-cd": G.noBareCd, "no-codex-call": G.noCodexAny, "no-exec-sentinel": G.noExecSentinel, "refusal": rx(REFUSE) } },
  { name: "parallel-one-fails", prompt: `/ask-codex:ask astra, sol ${Q}`, scenario: { exec: { by_model: { [SLUGS.astra]: { reply: REPLIES.astra }, [SLUGS.sol]: { mode: "fail" } } } },
    graders: { ...base([SLUGS.astra, SLUGS.sol]), "exec-twice": G.twoExec, "failed-line": rx(String.raw`Failed model: gpt-5\.6-sol`),
      "no-grouping": rx("Divergences", "not_contains"), "survivor-llm": llm(`
Two models were consulted; gpt-5.6-sol failed and gpt-6-astra answered with three claims (empty object on timeout; a circuit breaker; raising the timeout would fix it).
PASS if the final response presents gpt-6-astra's claims with dispositions, notes that gpt-5.6-sol failed and why, and attributes nothing to gpt-5.6-sol.
FAIL if any point is attributed to gpt-5.6-sol, the failure is not mentioned, or astra's claims are missing.`) } },
  { name: "parallel-shared-timer", prompt: `/ask-codex:ask astra, sol ${Q}`, env: { EVAL_ASK_CODEX_TIMEOUT_MINUTES: "1" }, taskTools: true,
    scenario: { exec: { by_model: { [SLUGS.sol]: { reply: REPLIES.sol }, [SLUGS.astra]: { mode: "slow-silent", duration_s: 600 } } } },
    graders: { ...base([SLUGS.astra, SLUGS.sol]), "exec-twice": G.twoExec, "used-taskstop": toolUsed("TaskStop", null, 1),
      "check-line": rx(String.raw`Parallel check: done [—-] gpt-5\.6-sol; still running [—-] gpt-6-astra`),
      "stopped-line": rx(String.raw`Failed model: gpt-6-astra [—-] stopped`), "sol-present": rx("AbortController"), "timer-llm": llm(`
Two models were consulted with a 1-minute check interval; gpt-5.6-sol finished quickly, gpt-6-astra produced no events and could not be asked about in this session.
PASS if the final response says gpt-5.6-sol finished and gpt-6-astra was stopped, presents gpt-5.6-sol's claims with dispositions, and attributes nothing to gpt-6-astra.
FAIL if it attributes any claim to gpt-6-astra, says it kept waiting, or omits gpt-5.6-sol's result.`) } },
];

if (process.argv[1] && import.meta.url.endsWith(path.basename(process.argv[1]))) {
  for (const c of CASES) {
    const dir = path.join(EVALS, c.name);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(path.join(dir, "graders"), { recursive: true });
    let yaml = `schema_version: "1.1"\nname: ${c.name}\ntags: [ticket-08]\ncontext:\n  scaffold_script: scaffold.sh\n  add_dirs: [stubbin]\n`;
    if (c.env) yaml += `execution:\n  env:\n${Object.entries(c.env).map(([k, v]) => `    ${k}: ${JSON.stringify(v)}`).join("\n")}\n`;
    fs.writeFileSync(path.join(dir, "case.yaml"), yaml);
    const tools = c.taskTools ? "[Skill, Bash, Read, Glob, Grep, Write, TaskOutput, TaskStop]" : "[Skill, Bash, Read, Glob, Grep, Write]";
    fs.writeFileSync(path.join(dir, "prompt.md"), `---\ndescription: ${JSON.stringify(c.name)}\nmax_turns: 40\ntimeout_seconds: 1200\nallowed_tools: ${tools}\n---\n\n${c.prompt}\n`);
    const s = `#!/usr/bin/env bash\nset -euo pipefail\n${GUARD}\nmkdir -p .stub src/pages "$HOME/.codex"\ncat > .stub/scenario.json <<'EOF'\n${JSON.stringify(c.scenario)}\nEOF\n` +
      `cat > src/user.js <<'EOF'\n${heredoc("src/user.js")}EOF\ncat > src/pages/profile.js <<'EOF'\n${heredoc("src/pages/profile.js")}EOF\n` +
      `cat > "$HOME/.codex/config.toml" <<'EOF'\n${CONFIG}EOF\ncat > "$HOME/.codex/models_cache.json" <<'EOF'\n${CACHE}EOF\n`;
    fs.writeFileSync(path.join(dir, "scaffold.sh"), s, { mode: 0o755 });
    for (const [g, content] of Object.entries(c.graders)) fs.writeFileSync(path.join(dir, "graders", `${g}.md`), content);
    console.log(`${c.name}: ${Object.keys(c.graders).length} graders`);
  }
}
