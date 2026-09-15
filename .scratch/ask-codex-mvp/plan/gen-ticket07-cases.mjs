// Generates the ticket-07 eval cases from slice-07.md (revision 3 + closing fix + deterministic graders).
// Usage: node gen-ticket07-cases.mjs <route>   route = 1..4 from the slice's route table
//   routes 1/3: TaskStop usable → case 2 keeps its TaskStop grader
//   routes 2/4: TaskStop unusable → case 2 without it
//   route 5 is not generated here (cases 1–2 move to ticket 09; generate only 3–4).
import fs from "node:fs";
import path from "node:path";

const EVALS = "D:/work_data/project/skill/ask-codex/evals";
const copy = (from) => fs.readFileSync(path.join(EVALS, from), "utf8");
const G = {
  skillFired: copy("diagnosis-blind/graders/skill-fired.md"),
  oneExec: copy("diagnosis-blind/graders/one-codex-exec.md"),
  noViolations: copy("diagnosis-blind/graders/no-violations.md"),
  noBareCd: copy("diagnosis-blind/graders/no-bare-cd.md"),
  tempCleanup: copy("diagnosis-blind/graders/temp-cleanup.md"),
  execSentinel: copy("diagnosis-blind/graders/exec-sentinel.md"),
};
const route = Number(process.argv[2]);
if (![1, 2, 3, 4, 5].includes(route)) throw new Error("usage: node gen-ticket07-cases.mjs <route 1..5>");
const stopUsable = route === 1 || route === 3;
const tools = route === 1 || route === 2 ? "[Skill, Bash, Read, Glob, Grep, Write, TaskOutput, TaskStop]" : "[Skill, Bash, Read, Glob, Grep, Write, TaskStop]";

const rx = (p) => `---\ntype: regex\npattern: '${p.replace(/'/g, "''")}'\n---\n`;
const llm = (t) => `---\ntype: llm\n---\n\n${t.trim()}\n`;
// The ticket-01 workspace (retry loop + profile page) matches the stub's default reply.
const T01 = fs.readFileSync(path.join(EVALS, "manual-with-question/scaffold.sh"), "utf8");
const heredoc = (file) => T01.split(`cat > ${file} <<'EOF'\n`)[1].split("EOF\n")[0];
const USER_JS = heredoc("src/user.js");
const PROFILE_JS = heredoc("src/pages/profile.js");
const Q = "/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?";
const exec = (extra) => ({ "skill-fired": G.skillFired, "one-codex-exec": G.oneExec, "no-violations": G.noViolations,
  "no-bare-cd": G.noBareCd, "temp-cleanup": G.tempCleanup, "exec-sentinel": G.execSentinel, ...extra });

export const CASES = [
  { name: "timeout-alive-notice", env: { EVAL_ASK_CODEX_TIMEOUT_MINUTES: "1" }, onlyRoutes: [1, 2, 3, 4],
    scenario: { exec: { mode: "slow-active", event_every_s: 5, duration_s: 100 } },
    graders: exec({ "override-active": rx("Timeout override active:"), "still-running": rx("Codex still running"), "alive-notice": llm(`
The timeout interval was overridden to 1 minute; Codex kept emitting progress events every few seconds and finished after about 100 seconds.
PASS if the final response states that the timeout override is active (1 minute) and that at least one liveness check found Codex still running with a recent last event, and it then presents Codex's claims with dispositions.
FAIL if it asks whether to wait or stop, reports the consultation as stopped, or presents no Codex result.`) }) },
  { name: "timeout-stalled-stop", env: { EVAL_ASK_CODEX_TIMEOUT_MINUTES: "1" }, onlyRoutes: [1, 2, 3, 4],
    scenario: { exec: { mode: "slow-silent", duration_s: 600 } },
    graders: { "skill-fired": G.skillFired, "one-codex-exec": G.oneExec, "no-bare-cd": G.noBareCd, "temp-cleanup": G.tempCleanup,
      "stopped-line": rx("Consultation stopped:"),
      ...(stopUsable ? { "used-taskstop": "---\ntype: tool_used\ntool: TaskStop\nmin: 1\n---\n" } : {}),
      "stop-report": llm(`
The timeout interval was overridden to 1 minute; Codex emitted no progress events, so the liveness check could not confirm it was alive and no one could answer a question in this session.
PASS if the final response (the stop report) states: the interval in force (a 1-minute override), the elapsed time, the last event and its age (or that there were no events), the two options that were offered — wait another interval / stop this consultation — with "stop" recommended, and that the consultation was stopped; and it attributes nothing to Codex.
FAIL if any of these is missing, if it claims Codex answered, or if it says it kept waiting.`) } },
  { name: "timeout-override-invalid-text", env: { EVAL_ASK_CODEX_TIMEOUT_MINUTES: "abc" }, onlyRoutes: [1, 2, 3, 4, 5], scenario: {},
    graders: exec({ "override-ignored": rx("Timeout override ignored:"), "names-value": rx("abc"), "ignored-notice": llm(`
The timeout override was set to "abc", which is not a positive whole number.
PASS if the final response says the override "abc" was ignored and the default of 30 minutes applies, and the consultation result is presented normally.
FAIL if it treats "abc" as a valid interval, says nothing about the override, or presents no Codex result.`) }) },
  { name: "timeout-override-invalid-zero", env: { EVAL_ASK_CODEX_TIMEOUT_MINUTES: "0" }, onlyRoutes: [1, 2, 3, 4, 5], scenario: {},
    graders: exec({ "override-ignored": rx("Timeout override ignored:"), "names-value": rx('"0"'), "ignored-notice": llm(`
The timeout override was set to "0", which is not a positive whole number.
PASS if the final response says the override "0" was ignored and the default of 30 minutes applies, and the consultation result is presented normally.
FAIL if it treats 0 as a valid interval, says nothing about the override, or presents no Codex result.`) }) },
];

const scaffoldFor = (scenario) => `#!/usr/bin/env bash\nset -euo pipefail\nmkdir -p .stub src/pages\ncat > .stub/scenario.json <<'EOF'\n${JSON.stringify(scenario)}\nEOF\ncat > src/user.js <<'EOF'\n${USER_JS}EOF\ncat > src/pages/profile.js <<'EOF'\n${PROFILE_JS}EOF\n`;
for (const c of CASES.filter((x) => x.onlyRoutes.includes(route))) {
  const dir = path.join(EVALS, c.name);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(path.join(dir, "graders"), { recursive: true });
  let yaml = `schema_version: "1.1"\nname: ${c.name}\ntags: [ticket-07]\ncontext:\n  scaffold_script: scaffold.sh\n  add_dirs: [stubbin]\n`;
  yaml += `execution:\n  env:\n${Object.entries(c.env).map(([k, v]) => `    ${k}: ${JSON.stringify(v)}`).join("\n")}\n`;
  fs.writeFileSync(path.join(dir, "case.yaml"), yaml);
  fs.writeFileSync(path.join(dir, "prompt.md"), `---\ndescription: ${JSON.stringify(c.name)}\nmax_turns: 40\ntimeout_seconds: 1200\nallowed_tools: ${tools}\n---\n\n${Q}\n`);
  fs.writeFileSync(path.join(dir, "scaffold.sh"), scaffoldFor(c.scenario), { mode: 0o755 });
  for (const [g, content] of Object.entries(c.graders)) fs.writeFileSync(path.join(dir, "graders", `${g}.md`), content);
  console.log(`${c.name}: ${Object.keys(c.graders).length} graders (route ${route})`);
}
