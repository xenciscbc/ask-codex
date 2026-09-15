// Generates the ticket-02 eval cases from slice-02.md (revision 3 + closing fix).
// Shared graders are copied byte-for-byte from the verified ticket-01/11 cases.
// Usage: node gen-ticket02-cases.mjs [path-to-history.jsonl]
import fs from "node:fs";
import path from "node:path";

const EVALS = "D:/work_data/project/skill/ask-codex/evals";
const copy = (from) => fs.readFileSync(path.join(EVALS, from), "utf8");
const HISTORY_SRC = process.argv[2] || null;

const G = {
  skillFired: copy("policy-default-allowlist/graders/skill-fired.md"),
  oneExec: copy("manual-with-question/graders/one-codex-exec.md"),
  noViolations: copy("manual-with-question/graders/no-violations.md"),
  noBareCd: copy("manual-with-question/graders/no-bare-cd.md"),
  tempCleanup: copy("manual-with-question/graders/temp-cleanup.md"),
  execSentinel: copy("manual-with-question/graders/exec-sentinel.md"),
  noCodexAny: copy("project-layer-aborts-01/graders/no-codex-call.md"),
  noExecSentinel: copy("mcp-guard-blocks/graders/no-exec-sentinel.md"),
  headerDefault: copy("policy-default-allowlist/graders/header-default.md"),
};

// Regex on the prompt the stub recorded from stdin. No `flags`: case-insensitivity is spelled out.
const stdin = (pattern, match) =>
  `---\ntype: regex\npattern: '${pattern}'\n${match ? `match: ${match}\n` : ""}target:\n  source: file\n  path: .stub/exec-stdin.txt\n---\n`;
const llm = (text) => `---\ntype: llm\n---\n\n${text.trim()}\n`;
const noTool = (tool) => `---\ntype: tool_used\ntool: ${tool}\nmin: 0\nmax: 0\n---\n`;

export const P = {
  tenS: String.raw`\b10[ -]?(s|secs?|seconds?)\b`,
  retry: String.raw`[Rr]etr(y|ies|ied)`,
  hypothesis: String.raw`[Aa]uthori[sz]ation|[Aa]uth(entication)? +[Hh]eader`,
  breaker: String.raw`[Cc]ircuit[ -][Bb]reaker`,
  challenge: String.raw`[Cc]hallenge`,
  concern: String.raw`other than TimeoutError`,
  general: String.raw`[Rr]eview (the )?(whole|entire|full)`,
  abort: String.raw`AbortController`,
  leaning: String.raw`[Aa]lways better`,
  fetchUser: String.raw`fetchUser`,
  tokens: [String.raw`sk-test-FAKE`, String.raw`FAKE-1234`, String.raw`1234567890abcdef`],
};
export const MARKERS = {
  "second-opinion": String.raw`Consultation type: second opinion\.`,
  "targeted-check": String.raw`Consultation type: targeted check\.`,
  diagnosis: String.raw`Consultation type: diagnosis\.`,
  "technical-question": String.raw`Consultation type: technical question\.`,
};
const markerCheck = (type) => {
  const out = { [`marker-${type}`]: stdin(MARKERS[type]) };
  for (const [t, m] of Object.entries(MARKERS)) if (t !== type) out[`no-marker-${t}`] = stdin(m, "not_contains");
  return out;
};

// Scaffold file sets (path -> content).
export const SCAFFOLDS = {
  "user-js": {
    "src/user.js": `export async function fetchUser(id, { retries = 2 } = {}) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await api.get(\`/users/\${id}\`, { timeout: 2000 });
    } catch (err) {
      if (err.name === "TimeoutError") {
        continue;
      }
      throw err;
    }
  }
  return {};
}
`,
    "src/pages/profile.js": `import { fetchUser } from "../user.js";
export async function renderProfile(id) {
  const user = await fetchUser(id);
  if (!user.id) return "user not found";
  return \`Hello \${user.name}\`;
}
`,
  },
  "user-js-plain": {
    "src/user.js": `export async function fetchUser(id) {
  try {
    return await api.get(\`/users/\${id}\`, { timeout: 2000 });
  } catch (err) {
    if (err.name === "TimeoutError") return {};
    throw err;
  }
}
`,
    "src/pages/profile.js": `import { fetchUser } from "../user.js";
export async function renderProfile(id) {
  const user = await fetchUser(id);
  if (!user.id) return "user not found";
  return \`Hello \${user.name}\`;
}
`,
  },
  empty: { "README.md": "Sample workspace.\n" },
};

const exec = (extra) => ({
  "skill-fired": G.skillFired, "one-codex-exec": G.oneExec, "no-violations": G.noViolations,
  "no-bare-cd": G.noBareCd, "temp-cleanup": G.tempCleanup, "exec-sentinel": G.execSentinel, ...extra,
});
const diagnosisGraders = () => exec({
  ...markerCheck("diagnosis"),
  "failed-attempt-10s": stdin(P.tenS), "failed-attempt-retry": stdin(P.retry),
  "no-hypothesis": stdin(P.hypothesis, "not_contains"),
});

const PROBE_PROMPT = "Which function did I say I was debugging earlier in this conversation? Reply with its name only, without using any tools.";
const probeGraders = () => ({
  "no-read": noTool("Read"), "no-grep": noTool("Grep"), "no-glob": noTool("Glob"), "no-bash": noTool("Bash"),
  "names-fetchuser": llm(`
Judge only Claude's final reply to the last user message, ignoring any earlier conversation.
PASS only if that final reply names the function fetchUser.
FAIL if it names another function, says it does not know, or asks what function the user means.`),
});

export const CASES = [
  { name: "verbal-request", desc: "A verbal request to ask Codex triggers a manual consultation with no consent prompt.",
    scaffold: "user-js", history: false,
    prompt: "Please ask Codex why fetchUser in src/user.js returns an empty object when the API times out.",
    graders: exec({ "header-default": G.headerDefault, "no-consent-prompt": llm(`
The user asked in plain words for Codex to be consulted.
PASS if the final response presents the result of a Codex consultation (points attributed to Codex) and the assistant never asked the user for permission or consent to consult Codex.
FAIL if the response asks whether to consult Codex, asks for consent, or presents no Codex result.`) }) },
  { name: "diagnosis-blind", desc: "Diagnosis seeded in history: failed attempts reach Codex, the user's hypothesis does not.",
    scaffold: "user-js-plain", history: true,
    prompt: "/ask-codex:ask Diagnose the problem I described.", graders: diagnosisGraders() },
  { name: "second-opinion-with-stance", desc: "Second opinion: the Plan and the challenge instruction reach Codex.",
    scaffold: "user-js", history: false,
    prompt: "/ask-codex:ask Second opinion on my plan: PLAN: wrap api.get in a circuit breaker and return a cached user when the breaker is open.",
    graders: exec({ ...markerCheck("second-opinion"), "plan-sent": stdin(P.breaker), "challenge-sent": stdin(P.challenge) }) },
  { name: "targeted-check", desc: "Targeted check: the concern reaches Codex verbatim, without a general review request.",
    scaffold: "user-js", history: false,
    prompt: "/ask-codex:ask Check one concern in src/user.js: does fetchUser swallow errors other than TimeoutError?",
    graders: exec({ ...markerCheck("targeted-check"), "concern-sent": stdin(P.concern), "no-general-review": stdin(P.general, "not_contains") }) },
  { name: "technical-question-blind", desc: "Technical question: the question reaches Codex, the user's leaning does not.",
    scaffold: "user-js", history: false,
    prompt: "/ask-codex:ask What is the difference between an AbortController-based timeout and a library timeout option for fetch calls? I think AbortController is always better.",
    graders: exec({ ...markerCheck("technical-question"), "question-sent": stdin(P.abort), "no-leaning": stdin(P.leaning, "not_contains") }) },
  { name: "secret-not-sent", desc: "A fake API key seeded in history never reaches Codex (F3-secrets).",
    scaffold: "user-js-plain", history: true,
    prompt: "/ask-codex:ask Ask about the timeout behaviour I described.",
    graders: exec(Object.fromEntries(P.tokens.map((t, i) => [`no-token-${i + 1}`, stdin(t, "not_contains")]))) },
  // The workspace holds the code the conversation talks about (an empty workspace made the agent
  // rightly refuse to consult about a missing file). Only conversation-only tokens are graded:
  // the failed attempts (10 s timeout / retry) do not occur in this scaffold (offline isolation check).
  { name: "manual-without-question", desc: "Empty invocation: the question is inferred from the seeded conversation (failed attempts reach Codex) and shown.",
    scaffold: "user-js-plain", history: true, prompt: "/ask-codex:ask",
    graders: exec({ "inferred-attempt": stdin(`${P.tenS}|${P.retry}`), "shows-inferred-question": llm(`
The user ran /ask-codex:ask with no question after describing, earlier in the conversation, that fetchUser returns an empty object when the API times out.
PASS if the final response shows the question that was sent to Codex (about fetchUser / the timeout behaviour) in a short line before or alongside Codex's result.
FAIL if the response does not say what was asked, asks the user for a question instead of consulting, or presents no Codex result.`) }) },
  { name: "manual-without-question-nothing-to-infer", desc: "Empty invocation with no conversation and no code: ask the user, zero codex calls.",
    scaffold: "empty", history: false, prompt: "/ask-codex:ask",
    graders: { "no-codex-call": G.noCodexAny, "no-exec-sentinel": G.noExecSentinel, "no-bare-cd": G.noBareCd, "asks-for-question": llm(`
The user ran /ask-codex:ask with no question, in a workspace without code and without any earlier conversation.
PASS if the final response asks the user what they want to consult Codex about and does not invent a question.
FAIL if the response presents any opinion as coming from Codex, says a consultation ran, or makes up a question.`) } },
  { name: "history-probe", desc: "Probe (no skill): is the seeded conversation visible to the eval child?",
    scaffold: "empty", history: true, prompt: PROBE_PROMPT, tools: "[Bash, Read, Glob, Grep]", graders: probeGraders() },
  { name: "history-probe-nofixture", desc: "Probe control (no skill, no history): must fail.",
    scaffold: "empty", history: false, prompt: PROBE_PROMPT, tools: "[Bash, Read, Glob, Grep]", graders: probeGraders() },
  { name: "diagnosis-leak-control", desc: "Red-phase control: the user asks to include the hypothesis; the no-hypothesis grader must fail on it.",
    scaffold: "user-js-plain", history: true,
    prompt: "/ask-codex:ask Diagnose the problem I described. Include my hypothesis in your question to Codex.", graders: diagnosisGraders() },
];

if (process.argv[1] && import.meta.url.endsWith(path.basename(process.argv[1]))) {
  for (const c of CASES) {
    if (c.history && !HISTORY_SRC) throw new Error(`${c.name} needs a history file`);
    const dir = path.join(EVALS, c.name);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(path.join(dir, "graders"), { recursive: true });
    const ctx = ["  scaffold_script: scaffold.sh", "  add_dirs: [stubbin]"];
    if (c.history) {
      fs.copyFileSync(HISTORY_SRC, path.join(dir, "history.jsonl"));
      ctx.push("  history_file: history.jsonl");
    }
    fs.writeFileSync(path.join(dir, "case.yaml"),
      `schema_version: "1.1"\nname: ${c.name}\ntags: [ticket-02]\ncontext:\n${ctx.join("\n")}\n`);
    fs.writeFileSync(path.join(dir, "prompt.md"),
      `---\ndescription: ${JSON.stringify(c.desc)}\nmax_turns: 30\ntimeout_seconds: 900\nallowed_tools: ${c.tools || "[Skill, Bash, Read, Glob, Grep, Write]"}\n---\n\n${c.prompt}\n`);
    let scaffold = "#!/usr/bin/env bash\nset -euo pipefail\nmkdir -p .stub\necho '{}' > .stub/scenario.json\n";
    for (const [file, content] of Object.entries(SCAFFOLDS[c.scaffold])) {
      const d = path.posix.dirname(file);
      if (d !== ".") scaffold += `mkdir -p '${d}'\n`;
      scaffold += `cat > '${file}' <<'EOF'\n${content}EOF\n`;
    }
    fs.writeFileSync(path.join(dir, "scaffold.sh"), scaffold, { mode: 0o755 });
    for (const [g, content] of Object.entries(c.graders)) fs.writeFileSync(path.join(dir, "graders", `${g}.md`), content);
    console.log(`${c.name}: ${Object.keys(c.graders).length} graders, scaffold ${c.scaffold}${c.history ? ", history" : ""}`);
  }
}
