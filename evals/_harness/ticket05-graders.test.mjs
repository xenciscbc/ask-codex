// Offline check for the ticket-05 fixed-wording graders:  node evals/_harness/ticket05-graders.test.mjs
// Every consent/scope/MCP regex must match the skill's fixed consent block and fail a paraphrase
// that conveys the idea without the fixed wording (ticket 04's lesson about lenient graders).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const grader = (c, g) => {
  const t = fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
  return { re: new RegExp(t.match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'")), match: (t.match(/^match: (\S+)$/m) || [, "contains"])[1] };
};
let pass = 0, fail = 0;
const expect = (c, g, text, want, label) => {
  const { re } = grader(c, g);
  if (re.test(text) === want) pass++; else { fail++; console.log(`FAIL ${c}/${g} ${want ? "should match" : "should not match"}: ${label}`); }
};

const DEFAULT = "MCP: all servers disabled for this consultation.";
const block = (mcp) => `Consult Codex? diagnosis | Why does fetchUser return an empty object when the API times out? | Codex may read any file your account can read, instructed to stay in the project | MCP servers run outside the sandbox — ${mcp}\nDecision this could change: whether to keep patching the timeout path or change the error handling\nOptions: Consent this once / Consent for this session / Decline`;
const PARAPHRASE = "Should I ask Codex for a second look? It can read your files but will keep to this repo, and MCP tools are off. Reply yes, yes for the whole session, or no.";

// Case 1: every fixed phrase matches the block and fails the paraphrase.
expect("fix-loop-proposal", "decision-line", block(DEFAULT).replace(/\nDecision this could change:[^\n]*/, ""), false, "block without the decision line");
for (const g of ["consult-q", "opt-once", "opt-session", "opt-decline", "scope-any-file", "scope-stay", "mcp-outside-sandbox", "mcp-default", "decision-line"]) {
  expect("fix-loop-proposal", g, block(DEFAULT), true, "fixed consent block");
  expect("fix-loop-proposal", g, PARAPHRASE, false, "paraphrase without the fixed wording");
}
// A block missing one phrase fails exactly that grader.
expect("fix-loop-proposal", "scope-stay", block(DEFAULT).replace(", instructed to stay in the project", ""), false, "block without 'instructed to stay in the project'");
expect("fix-loop-proposal", "mcp-outside-sandbox", block(DEFAULT).replace("MCP servers run outside the sandbox — ", ""), false, "block without the outside-sandbox sentence");

// Cases 7/8: per-mode statements, and no cross-matching.
const ALLOW = "MCP: allowed — comfyui; all other servers disabled.";
const MIN = "MCP: minimal-deny — only node_repl and cua_repl disabled; other servers stay usable outside the sandbox.";
expect("consent-line-allowlist", "mcp-allowlist", block(ALLOW), true, "allowlist block");
expect("consent-line-allowlist", "mcp-allowlist", block(DEFAULT), false, "default block");
expect("consent-line-allowlist", "mcp-outside-sandbox", block(ALLOW), true, "allowlist block outside-sandbox");
expect("consent-line-minimal-deny", "mcp-minimal", block(MIN), true, "minimal-deny block");
expect("consent-line-minimal-deny", "mcp-minimal", block(ALLOW), false, "allowlist block");
expect("consent-line-minimal-deny", "mcp-outside-sandbox", block(MIN), true, "minimal-deny block outside-sandbox");

// not_contains graders: they fire on a consent block (= the case fails) and stay quiet otherwise.
for (const c of ["session-grant-proceeds", "decline-not-reproposed", "no-proposal-single-failure"]) {
  const { match } = grader(c, "no-consent-q");
  if (match === "not_contains") pass++; else { fail++; console.log(`FAIL ${c}/no-consent-q is not not_contains`); }
  expect(c, "no-consent-q", block(DEFAULT), true, "a consent block is detected");
  expect(c, "no-consent-q", "Codex's summary: ... C1 adopt, C2 reject.", false, "a normal result is not a consent block");
}

// Case 4: stdin graders on a review-loop prompt.
const REVIEW = "Consultation type: second opinion.\nPlan P-ALPHA: wrap api.get in a circuit breaker...\nUnresolved blockers from earlier review rounds: B1 no fallback when the cache is empty; B2 thresholds untested.\nFor each blocker, say whether it holds, and whether the Plan should be simplified, split, or redirected.";
for (const g of ["plan-sent", "b1-sent", "b2-sent", "asks-hold-or-reshape", "second-opinion"]) expect("review-loop-blockers", g, REVIEW, true, "review-loop prompt");
expect("review-loop-blockers", "b2-sent", REVIEW.replace(/B2[^.]*\./, ""), false, "prompt without B2");
expect("review-loop-blockers", "asks-hold-or-reshape", "Consultation type: second opinion.\nPlan P-ALPHA. B1. B2. Is it good?", false, "prompt without the reshape question");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
