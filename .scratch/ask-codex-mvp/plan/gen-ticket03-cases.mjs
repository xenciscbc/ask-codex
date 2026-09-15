// Generates the ticket-03 eval cases from slice-03.md (revision 2). Route A: each scaffold seeds
// the throwaway $HOME/.codex after a guard that refuses any HOME outside the eval sandbox.
// Usage: node gen-ticket03-cases.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const EVALS = "D:/work_data/project/skill/ask-codex/evals";
const FIX = path.join(path.dirname(fileURLToPath(import.meta.url)), "t03-fixture");
const copy = (from) => fs.readFileSync(path.join(EVALS, from), "utf8");
const CACHE = fs.readFileSync(path.join(FIX, "models_cache.json"), "utf8");
const CONFIG = fs.readFileSync(path.join(FIX, "config.toml"), "utf8");

const G = {
  skillFired: copy("diagnosis-blind/graders/skill-fired.md"),
  oneExec: copy("diagnosis-blind/graders/one-codex-exec.md"),
  noViolations: copy("diagnosis-blind/graders/no-violations.md"),
  noBareCd: copy("diagnosis-blind/graders/no-bare-cd.md"),
  tempCleanup: copy("diagnosis-blind/graders/temp-cleanup.md"),
  execSentinel: copy("diagnosis-blind/graders/exec-sentinel.md"),
  noCodexAny: copy("manual-without-question-nothing-to-infer/graders/no-codex-call.md"),
  noExecSentinel: copy("manual-without-question-nothing-to-infer/graders/no-exec-sentinel.md"),
};

export const GUARD = `case "$HOME" in *claude-eval*) ;; *) echo "refusing to seed a Codex home outside the eval sandbox: HOME=$HOME" >&2; exit 1;; esac`;
const argv = (pattern, match) =>
  `---\ntype: regex\npattern: '${pattern}'\n${match ? `match: ${match}\n` : ""}target:\n  source: file\n  path: .stub/exec-argv.json\n---\n`;
const llm = (text) => `---\ntype: llm\n---\n\n${text.trim()}\n`;
// exec-argv.json is a JSON array, so the value after "-m" is the next string and -c values carry \" escapes.
export const A = {
  model: (slug) => String.raw`"-m",\s*"` + slug.replace(/\./g, String.raw`\.`) + `"`,
  effort: (e) => String.raw`model_reasoning_effort=\\"` + e + String.raw`\\"`,
};

const USER_JS = `export async function fetchUser(id) {
  try {
    return await api.get(\`/users/\${id}\`, { timeout: 2000 });
  } catch (err) {
    if (err.name === "TimeoutError") return {};
    throw err;
  }
}
`;
const Q = "Why does fetchUser in src/user.js return an empty object when the API times out?";

const scaffold = (seed) => {
  let s = "#!/usr/bin/env bash\nset -euo pipefail\n";
  if (seed) s += `${GUARD}\n`;
  s += "mkdir -p .stub src\necho '{}' > .stub/scenario.json\n";
  s += `cat > src/user.js <<'EOF'\n${USER_JS}EOF\n`;
  if (seed) {
    s += `mkdir -p "$HOME/.codex"\n`;
    s += `cat > "$HOME/.codex/config.toml" <<'EOF'\n${CONFIG}EOF\n`;
    s += `cat > "$HOME/.codex/models_cache.json" <<'EOF'\n${CACHE}EOF\n`;
  }
  return s;
};

const exec = (extra) => ({
  "skill-fired": G.skillFired, "one-codex-exec": G.oneExec, "no-violations": G.noViolations,
  "no-bare-cd": G.noBareCd, "temp-cleanup": G.tempCleanup, "exec-sentinel": G.execSentinel, ...extra,
});
const stop = (extra) => ({ "no-bare-cd": G.noBareCd, "no-codex-call": G.noCodexAny, "no-exec-sentinel": G.noExecSentinel, ...extra });

// History for cases 9 and 11: the user set astra for the rest of the session earlier.
export const SESSION_HISTORY = [
  { parentUuid: null, isSidechain: false, type: "user",
    message: { role: "user", content: "For the rest of this session, use astra for Codex consultations." },
    uuid: "3c2a1b0d-7e6f-4a5b-8c9d-0e1f2a3b4c01", timestamp: "2026-09-15T12:00:00.000Z", userType: "external",
    entrypoint: "sdk-cli", cwd: "/tmp/ask-codex-fixture", sessionId: "8e4d2c1a-6b5f-4e3d-9c2b-1a0f9e8d7c60", version: "2.1.272", gitBranch: "HEAD" },
  { parentUuid: "3c2a1b0d-7e6f-4a5b-8c9d-0e1f2a3b4c01", isSidechain: false, type: "assistant",
    message: { model: "claude-haiku-4-5-20251001", id: "msg_fixture_0003", type: "message", role: "assistant",
      content: [{ type: "text", text: "Noted." }], stop_reason: "end_turn", stop_sequence: null, usage: { input_tokens: 10, output_tokens: 3 } },
    uuid: "3c2a1b0d-7e6f-4a5b-8c9d-0e1f2a3b4c02", timestamp: "2026-09-15T12:00:02.000Z", userType: "external",
    entrypoint: "sdk-cli", cwd: "/tmp/ask-codex-fixture", sessionId: "8e4d2c1a-6b5f-4e3d-9c2b-1a0f9e8d7c60", version: "2.1.272", gitBranch: "HEAD" },
].map((o) => JSON.stringify(o)).join("\n") + "\n";

export const CASES = [
  { name: "alias-sol", desc: "Alias sol resolves to gpt-5.6-sol with default effort high.", prompt: `/ask-codex:ask sol ${Q}`,
    graders: exec({ "model-sol": argv(A.model("gpt-5.6-sol")), "effort-high": argv(A.effort("high")) }) },
  { name: "alias-astra", desc: "Alias astra resolves to gpt-6-astra with effort medium; without AskUserQuestion the choice applies to this consultation only.",
    prompt: `/ask-codex:ask astra ${Q}`,
    graders: exec({ "model-astra": argv(A.model("gpt-6-astra")), "effort-medium": argv(A.effort("medium")), "scope-note": llm(`
The user named the model astra for this consultation; the session default is a different model, and the assistant could not ask whether the choice should last for the rest of the session.
PASS if the final response says that the model choice (astra / gpt-6-astra) applies to this consultation only.
FAIL if it says the choice applies to the rest of the session, or says nothing about how long the choice applies.`) }) },
  { name: "alias-sol-low", desc: "sol:low is raised to medium with a note.", prompt: `/ask-codex:ask sol:low ${Q}`,
    graders: exec({ "model-sol": argv(A.model("gpt-5.6-sol")), "effort-medium": argv(A.effort("medium")), "no-effort-low": argv(A.effort("low"), "not_contains"), "low-raised-note": llm(`
The user asked for effort low; consultations never run below medium.
PASS if the final response notes that the requested low effort was raised to medium.
FAIL if it does not mention the change, or claims low was used.`) }) },
  { name: "alias-ambiguous", desc: "Alias 5.6 matches three models: ask with the candidates, zero codex calls.", prompt: `/ask-codex:ask 5.6 ${Q}`, stopCase: true,
    graders: stop({ "asks-candidates": llm(`
The alias 5.6 matches three listed models: gpt-5.6-sol, gpt-5.6-terra and gpt-5.6-luna.
PASS if the final response asks the user to choose a model and names all three candidates.
FAIL if it picks one on its own, presents any opinion as coming from Codex, or omits a candidate.`) }) },
  { name: "alias-unknown", desc: "model nova matches nothing: error listing the available models, zero codex calls.", prompt: `/ask-codex:ask model nova ${Q}`, stopCase: true,
    graders: stop({ "lists-available": llm(`
No listed model matches "nova". The publicly listed models are gpt-6-astra, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna and gpt-5.5; gpt-reserve and codex-auto-review are hidden.
PASS if the final response says no model matches and lists the available models (all five listed ones), without offering gpt-reserve or codex-auto-review.
FAIL if it runs the consultation, picks a model on its own, omits listed models, or offers a hidden model.`) }) },
  { name: "alias-metachar", desc: "F9: a model token with shell metacharacters is rejected, zero codex calls.", prompt: "/ask-codex:ask sol;touch${IFS}pwned " + Q, stopCase: true,
    graders: stop({ "no-pwned-file": "---\ntype: file_exists\npath: pwned\nexists: false\n---\n", "rejects-token": llm(`
The first word of the request, "sol;touch\${IFS}pwned", is a model name containing shell metacharacters.
PASS if the final response rejects it as an invalid model name and does not run the consultation.
FAIL if it runs the consultation, silently strips the characters and continues, or presents any opinion as coming from Codex.`) }) },
  { name: "effort-unsupported", desc: "gpt-5.5:max is clamped to xhigh (the model's highest level) with a note.", prompt: `/ask-codex:ask gpt-5.5:max ${Q}`,
    graders: exec({ "model-55": argv(A.model("gpt-5.5")), "effort-xhigh": argv(A.effort("xhigh")), "no-effort-max": argv(A.effort("max"), "not_contains"), "clamp-note": llm(`
The user asked for effort max, which gpt-5.5 does not support; its highest level is xhigh.
PASS if the final response notes that max is not supported by this model and xhigh was used instead.
FAIL if it does not mention the change, or claims max was used.`) }) },
  { name: "default-model-config", desc: "No model named: the Codex-configured model with effort medium; the configured effort low never reaches argv.", prompt: `/ask-codex:ask ${Q}`,
    graders: exec({ "model-terra": argv(A.model("gpt-5.6-terra")), "effort-medium": argv(A.effort("medium")), "no-effort-low": argv(A.effort("low"), "not_contains") }) },
  { name: "session-override-persists", desc: "A session-scoped model choice stated earlier is used by a later consultation.", prompt: `/ask-codex:ask ${Q}`, history: true,
    graders: exec({ "model-astra": argv(A.model("gpt-6-astra")), "effort-medium": argv(A.effort("medium")) }) },
  { name: "override-restated-no-prompt", desc: "Re-stating the session setting asks nothing and adds no scope note.", prompt: `/ask-codex:ask astra ${Q}`, history: true,
    graders: exec({ "model-astra": argv(A.model("gpt-6-astra")), "no-scope-prompt": llm(`
Earlier in this conversation the user chose astra for the rest of the session; now they named astra again.
PASS if the final response presents the consultation result without asking whether the choice applies to this consultation or the session, and without a note that the model applies to this consultation only.
FAIL if it asks about the scope of the choice or says the choice applies to this consultation only.`) }) },
];

export const PROBE = {
  name: "codex-home-probe", desc: "Probe (no skill): can a scaffold seed the throwaway Codex home, and can the agent read it?",
  prompt: "Run `printenv HOME`, then Read the file `.codex/models_cache.json` inside that home directory and reply with only the slug of the model whose priority is 4.",
  graders: {
    "reads-seeded-cache": "---\ntype: regex\npattern: 'gpt-5\\.6-sol'\n---\n",
    "scaffold-home-is-eval": "---\ntype: regex\npattern: 'claude-eval'\ntarget:\n  source: file\n  path: .stub/scaffold-home.txt\n---\n",
  },
};

if (process.argv[1] && import.meta.url.endsWith(path.basename(process.argv[1]))) {
  const write = (c, scaffoldText, tools) => {
    const dir = path.join(EVALS, c.name);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(path.join(dir, "graders"), { recursive: true });
    const ctx = ["  scaffold_script: scaffold.sh", "  add_dirs: [stubbin]"];
    if (c.history) { fs.writeFileSync(path.join(dir, "history.jsonl"), SESSION_HISTORY); ctx.push("  history_file: history.jsonl"); }
    fs.writeFileSync(path.join(dir, "case.yaml"), `schema_version: "1.1"\nname: ${c.name}\ntags: [ticket-03]\ncontext:\n${ctx.join("\n")}\n`);
    fs.writeFileSync(path.join(dir, "prompt.md"),
      `---\ndescription: ${JSON.stringify(c.desc)}\nmax_turns: 30\ntimeout_seconds: 900\nallowed_tools: ${tools}\n---\n\n${c.prompt}\n`);
    fs.writeFileSync(path.join(dir, "scaffold.sh"), scaffoldText, { mode: 0o755 });
    for (const [g, content] of Object.entries(c.graders)) fs.writeFileSync(path.join(dir, "graders", `${g}.md`), content);
    console.log(`${c.name}: ${Object.keys(c.graders).length} graders${c.history ? ", history" : ""}`);
  };
  const only = process.argv[2];
  if (!only || only === "probe") write(PROBE, scaffold(true) + `printf '%s\\n' "$HOME" > .stub/scaffold-home.txt\n`, "[Bash, Read]");
  if (!only || only === "cases") for (const c of CASES) write(c, scaffold(true), "[Skill, Bash, Read, Glob, Grep, Write]");
}
