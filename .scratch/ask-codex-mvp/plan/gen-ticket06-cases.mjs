// Generates the ticket-06 eval cases (slice-06 revision 1 draft; adjust after its review).
// Usage: node gen-ticket06-cases.mjs
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
const T01 = copy("manual-with-question/scaffold.sh");
const heredoc = (file) => T01.split(`cat > ${file} <<'EOF'\n`)[1].split("EOF\n")[0];
const rx = (p, match) => `---\ntype: regex\npattern: '${p.replace(/'/g, "''")}'\n${match ? `match: ${match}\n` : ""}---\n`;
const onFile = (file, p, match) => `---\ntype: regex\npattern: '${p.replace(/'/g, "''")}'\n${match ? `match: ${match}\n` : ""}target:\n  source: file\n  path: ${file}\n---\n`;
const llm = (t) => `---\ntype: llm\n---\n\n${t.trim()}\n`;

// History: the earlier consultation, as Claude presented it (hand-written, ticket-02 format).
const PRIOR = `Asked Codex (diagnosis, gpt-5.6-sol, high) why fetchUser returns an empty object when the API times out.
MCP: all servers disabled for this consultation.

Codex's summary: the retry loop in fetchUser swallows the timeout error, so callers see an empty result instead of a failure.

- C1 (fact, high): fetchUser catches TimeoutError and returns an empty object instead of rethrowing. Evidence: src/user.js:7. **Adopt** — matches the code.
- C2 (inference, medium): renderProfile treats an empty object as 'user not found', which explains the misleading page. Evidence: src/pages/profile.js:4. **Investigate** — plausible, but I have not confirmed that no other path renders "user not found".
- C3 (inference, low): raising the timeout from 2s to 10s would hide the symptom without fixing the error handling. **Reject** — true but not the question asked.`;
const SESSION = "4d3c2b1a-0f9e-4d8c-8b7a-6f5e4d3c2b10";
const lines = [
  { parentUuid: null, type: "user", message: { role: "user", content: "/ask-codex:ask Why does fetchUser in src/user.js return an empty object when the API times out?" }, uuid: "5e4d3c2b-1a0f-4e9d-8c7b-000000000001" },
  { parentUuid: "5e4d3c2b-1a0f-4e9d-8c7b-000000000001", type: "assistant",
    message: { model: "claude-haiku-4-5-20251001", id: "msg_fixture_0601", type: "message", role: "assistant", content: [{ type: "text", text: PRIOR }], stop_reason: "end_turn", stop_sequence: null, usage: { input_tokens: 10, output_tokens: 200 } },
    uuid: "5e4d3c2b-1a0f-4e9d-8c7b-000000000002" },
].map((o, i) => JSON.stringify({ ...o, isSidechain: false, timestamp: `2026-09-15T12:00:0${i}.000Z`, userType: "external", entrypoint: "sdk-cli", cwd: "/tmp/ask-codex-fixture", sessionId: SESSION, version: "2.1.272", gitBranch: "HEAD" }));
const HISTORY = lines.join("\n") + "\n";

// Case 4: an earlier consultation reviewed Plan P-BETA; the user then revised it.
const PRIOR_BETA = `Asked Codex (second opinion, gpt-5.6-sol, high) to check Plan P-BETA: serve the last cached user when the API times out.
MCP: all servers disabled for this consultation.

- C1 (inference, medium): P-BETA has no fallback when the cache is empty, so first-time visitors still see 'user not found'. **Investigate** — likely, need to confirm how often the cache is cold.
- C2 (fact, high): P-BETA hides timeouts from monitoring, because the cached path never reports the failure. **Adopt** — the plan has no logging.
- C3 (inference, low): the cache could serve stale profile names for hours. **Reject** — names change rarely and the cache is per request.`;
const SESSION_B = "7f6e5d4c-3b2a-4190-8a7b-6c5d4e3f2a10";
const turnsB = [
  ["user", "Plan P-BETA: serve the last cached user when the API times out. /ask-codex:ask Second opinion on P-BETA."],
  ["assistant", PRIOR_BETA],
  ["user", "P-BETA v2: fall back to a placeholder user when the cache is empty, and log each timeout to monitoring."],
  ["assistant", "Noted — P-BETA v2 addresses the empty-cache case and the missing monitoring."],
];
let parentB = null;
const HISTORY_REVISED = turnsB.map(([role, text], i) => {
  const uuid = `8a7b6c5d-4e3f-4a1b-9c0d-00000000000${i + 1}`;
  const message = role === "user" ? { role: "user", content: text }
    : { model: "claude-haiku-4-5-20251001", id: `msg_fixture_060${i + 2}`, type: "message", role: "assistant", content: [{ type: "text", text }], stop_reason: "end_turn", stop_sequence: null, usage: { input_tokens: 10, output_tokens: 100 } };
  const o = { parentUuid: parentB, isSidechain: false, type: role, message, uuid, timestamp: `2026-09-15T12:10:0${i}.000Z`, userType: "external", entrypoint: "sdk-cli", cwd: "/tmp/ask-codex-fixture", sessionId: SESSION_B, version: "2.1.272", gitBranch: "HEAD" };
  parentB = uuid;
  return JSON.stringify(o);
}).join("\n") + "\n";

const claim = (id, statement, followup_status, kind = "inference", evidence = []) => ({ id, statement, kind, confidence: "medium", evidence, followup_status });
const C2 = "renderProfile treats an empty object as 'user not found', which explains the misleading page.";
const REPLIES = {
  resolved: { summary: "C2 holds: renderProfile is the only place that renders 'user not found'.", claims: [claim("C2", C2, "resolved", "fact", ["src/pages/profile.js:4"])], open_questions: [] },
  newBlocking: { summary: "C2 is still open; a new blocking issue was found.", claims: [
    claim("C2", C2, "unresolved", "inference", ["src/pages/profile.js:4"]),
    claim("C4", "fetchUser also swallows AbortError the same way, so cancelled requests look like missing users.", "new-blocking", "fact", ["src/user.js:6"]),
    claim("C5", "Consider renaming fetchUser to loadUser for clarity.", null),
  ], open_questions: [] },
};

const PROMPT = "/ask-codex:ask Follow up with Codex on the claim you marked investigate.";
const base = (extra) => ({ "skill-fired": G.skillFired, "one-codex-exec": G.oneExec, "no-violations": G.noViolations, "no-bare-cd": G.noBareCd,
  "temp-cleanup": G.tempCleanup, "exec-sentinel": G.execSentinel, "no-resume": onFile(".stub/exec-argv.json", "resume|fork", "not_contains"),
  "stdin-marker": onFile(".stub/exec-stdin.txt", "Consultation type: follow-up\\."),
  "stdin-c2-line": onFile(".stub/exec-stdin.txt", "C2 \\[investigate\\][^\\n]*renderProfile"),
  "stdin-c2-reason": onFile(".stub/exec-stdin.txt", "C2 \\[investigate\\][^\\n]*— Claude:"), ...extra });

export const CASES = [
  { name: "followup-carries-claims", reply: REPLIES.resolved, graders: base({
      "not-carried-c1": onFile(".stub/exec-stdin.txt", "C1 \\[adopt\\]", "not_contains"), "not-carried-c3": onFile(".stub/exec-stdin.txt", "C3 \\[reject\\]", "not_contains"),
      "c2-resolved": rx("C2[`*\\s]*\\[resolved\\]"), "c2-updated": rx("C2[^\\n]*Updated disposition"), "status-shown": llm(`
Earlier Claude marked Codex's claim C2 ("renderProfile treats an empty object as 'user not found'") as investigate; in this follow-up Codex reported C2 as resolved.
PASS if the final response shows C2 with its follow-up status (resolved) and Claude's updated disposition for it with a reason.
FAIL if C2's status or the updated disposition is missing, or the response presents the follow-up as a brand-new consultation with fresh claim numbering.`) }) },
  { name: "followup-new-blocking", reply: REPLIES.newBlocking, graders: base({
      "c2-unresolved": rx("C2[`*\\s]*\\[unresolved\\]"), "c2-updated": rx("C2[^\\n]*Updated disposition"),
      "heading": rx("New blocking claim from Codex"), "c4-shown": rx("AbortError"), "c5-omitted": rx("loadUser", "not_contains"), "c5-not-mentioned": rx("\\bC5\\b", "not_contains"), "presentation": llm(`
In this follow-up Codex reported C2 as unresolved, added C4 as a new blocking claim (fetchUser also swallows AbortError), and added C5 (rename fetchUser to loadUser) without marking it blocking.
PASS if the final response shows C2 as unresolved with Claude's updated disposition, lists C4 separately as a new blocking claim with a disposition, and does not present C5 as a claim.
FAIL if C4 is mixed in with the carried claims without being flagged as new and blocking, C5 is presented as a claim, or C2's status is missing.`) }) },
  { name: "followup-revised-plan", history: HISTORY_REVISED, prompt: "/ask-codex:ask Re-check the revised plan with Codex.",
    reply: { summary: "P-BETA v2 addresses both earlier concerns.", claims: [
      claim("C1", "P-BETA has no fallback when the cache is empty, so first-time visitors still see 'user not found'.", "resolved"),
      claim("C2", "P-BETA hides timeouts from monitoring, because the cached path never reports the failure.", "resolved", "fact")], open_questions: [] },
    graders: { "skill-fired": G.skillFired, "one-codex-exec": G.oneExec, "no-violations": G.noViolations, "no-bare-cd": G.noBareCd,
      "temp-cleanup": G.tempCleanup, "exec-sentinel": G.execSentinel, "no-resume": onFile(".stub/exec-argv.json", "resume|fork", "not_contains"),
      "stdin-marker": onFile(".stub/exec-stdin.txt", "Consultation type: follow-up\\."),
      "not-second-opinion": onFile(".stub/exec-stdin.txt", "Consultation type: second opinion\\.", "not_contains"),
      "stdin-c1-line": onFile(".stub/exec-stdin.txt", "C1 \\[investigate\\][^\\n]*fallback"),
      "stdin-c2-line": onFile(".stub/exec-stdin.txt", "C2 \\[adopt\\][^\\n]*monitoring"),
      "stdin-revision": onFile(".stub/exec-stdin.txt", "P-BETA v2"),
      "c1-resolved": rx("C1[`*\\s]*\\[resolved\\]"), "c1-updated": rx("C1[^\\n]*Updated disposition") } },
];

if (process.argv[1] && import.meta.url.endsWith(path.basename(process.argv[1]))) {
  for (const c of CASES) {
    const dir = path.join(EVALS, c.name);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(path.join(dir, "graders"), { recursive: true });
    fs.writeFileSync(path.join(dir, "history.jsonl"), c.history || HISTORY);
    fs.writeFileSync(path.join(dir, "case.yaml"), `schema_version: "1.1"\nname: ${c.name}\ntags: [ticket-06]\ncontext:\n  scaffold_script: scaffold.sh\n  history_file: history.jsonl\n  add_dirs: [stubbin]\n`);
    fs.writeFileSync(path.join(dir, "prompt.md"), `---\ndescription: ${JSON.stringify(c.name)}\nmax_turns: 30\ntimeout_seconds: 900\nallowed_tools: [Skill, Bash, Read, Glob, Grep, Write]\n---\n\n${c.prompt || PROMPT}\n`);
    fs.writeFileSync(path.join(dir, "scaffold.sh"),
      `#!/usr/bin/env bash\nset -euo pipefail\nmkdir -p .stub src/pages\ncat > .stub/scenario.json <<'EOF'\n${JSON.stringify({ exec: { reply: c.reply } })}\nEOF\ncat > src/user.js <<'EOF'\n${heredoc("src/user.js")}EOF\ncat > src/pages/profile.js <<'EOF'\n${heredoc("src/pages/profile.js")}EOF\n`, { mode: 0o755 });
    for (const [g, content] of Object.entries(c.graders)) fs.writeFileSync(path.join(dir, "graders", `${g}.md`), content);
    console.log(`${c.name}: ${Object.keys(c.graders).length} graders`);
  }
}
