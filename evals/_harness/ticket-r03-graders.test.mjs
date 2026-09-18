// Offline check for the reliability slice-03 graders (stop path through run.sh/stop.sh):
//   node evals/_harness/ticket-r03-graders.test.mjs
// Each regex grader must pass the exact line stop.sh prints (with and without markdown around
// the fixed words) and fail a missing field, a NOT-confirmed ending, a paraphrase, and — for the
// trace graders — a trace where the line sits only in a tool result or only after TaskStop.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const evals = path.join(repo, "evals");
const grader = (c, g) => {
  const t = fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
  const key = /^input_match:/m.test(t) ? "input_match" : "pattern";
  const m = t.match(new RegExp(`^${key}: '((?:[^']|'')*)'$`, "m"));
  return new RegExp(m[1].replace(/''/g, "'"));
};
const has = (c, g, text) => grader(c, g).test(text);
let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

// The exact shape stop.sh prints (see run-stop-scripts.test.mjs FIELDS).
const LINE = "Consultation stopped: interval 1 minutes (override); elapsed 1:14; last event turn.started 1:13 ago; offered: wait another 1 minutes / stop (recommended: stop); process tree ended";
const BOLD = "**Consultation stopped:** interval 1 minutes (override); elapsed 1:14; last event turn.started 1:13 ago; offered: wait another 1 minutes / stop (recommended: stop); process tree ended";
const NO_EVENTS = "Consultation stopped: interval 30 minutes (default); elapsed 31:02; no events; offered: wait another 30 minutes / stop (recommended: stop); process tree ended";
const SUFFIX = "; done — gpt-5.6-sol; still running — gpt-6-astra";
const NOT_CONFIRMED = LINE.replace("process tree ended", "process tree NOT confirmed — pids 4242");
const NO_OFFERED = LINE.replace("offered: wait another 1 minutes / stop (recommended: stop); ", "");
const NO_ELAPSED = LINE.replace("elapsed 1:14; ", "");
const PARAPHRASE = "I stopped the consultation after about 74 seconds; the last event was turn.started and the process tree has ended. The options were to wait another minute or stop, and I recommended stopping.";

// Last-message graders.
for (const [label, text, ok] of [
  ["exact line", LINE, true], ["bold fixed words", BOLD, true], ["no events variant", NO_EVENTS, true],
  ["with parallel suffix", LINE + SUFFIX, true], ["inside a reply", `Report:\n\n${BOLD}\n\nMy own view…`, true],
  ["NOT confirmed", NOT_CONFIRMED, false], ["missing offered", NO_OFFERED, false], ["missing elapsed", NO_ELAPSED, false], ["paraphrase", PARAPHRASE, false],
]) check(has("timeout-stalled-stop", "stopped-line", text) === ok, `stopped-line: ${label} → ${ok ? "pass" : "fail"}`);

for (const [label, text, ok] of [
  ["line + suffix", LINE + SUFFIX, true], ["bold + backticked slugs + hyphen", BOLD + "; done - `gpt-5.6-sol`; still running - `gpt-6-astra`", true],
  ["no suffix", LINE, false], ["swapped models", LINE + "; done — gpt-6-astra; still running — gpt-5.6-sol", false],
  ["aliases", LINE + "; done — sol; still running — astra", false], ["NOT confirmed + suffix", NOT_CONFIRMED + SUFFIX, false],
]) check(has("parallel-shared-timer", "stopped-report", text) === ok, `stopped-report: ${label} → ${ok ? "pass" : "fail"}`);

// Trace graders: one JSON message per line, as claude plugin eval writes trace.jsonl.
const A = (text) => JSON.stringify({ type: "assistant", message: { role: "assistant", content: [{ type: "text", text }] } });
const TOOL = (name, input) => JSON.stringify({ type: "assistant", message: { role: "assistant", content: [{ type: "tool_use", name, input }] } });
const RESULT = (content) => JSON.stringify({ type: "user", message: { role: "user", content: [{ type: "tool_result", tool_use_id: "x", content }] } });
const STOP_CMD = { command: "bash '/p/skills/ask/scripts/stop.sh' '/t/ask-codex/run.a' --interval 1 --interval-source override --recommended stop --done 'gpt-5.6-sol' --still-running 'gpt-6-astra'" };
const TASKSTOP = TOOL("TaskStop", { task_id: "b1" });
const trace = (...lines) => lines.join("\n") + "\n";

const GOOD = trace(A("Checking liveness."), TOOL("Bash", STOP_CMD), RESULT(LINE + SUFFIX), A(BOLD + SUFFIX + "\n\nStopping the task now."), TASKSTOP, A("Cleaning up."));
const TOOL_RESULT_ONLY = trace(A("Checking liveness."), TOOL("Bash", STOP_CMD), RESULT(LINE + SUFFIX), TASKSTOP, A("Cleaning up."), A(LINE + SUFFIX));
const AFTER_ONLY = trace(A("Checking liveness."), TOOL("Bash", STOP_CMD), RESULT(LINE + SUFFIX), TASKSTOP, A(LINE + SUFFIX));
const NO_TASKSTOP = trace(A("Checking liveness."), TOOL("Bash", STOP_CMD), RESULT(LINE + SUFFIX), A(LINE + SUFFIX));
const NOT_CONFIRMED_TRACE = trace(TOOL("Bash", STOP_CMD), RESULT(NOT_CONFIRMED), A(NOT_CONFIRMED), TASKSTOP);
const NOTICE_THEN_STOP = trace(A("Codex still running — 1:02 elapsed; done — gpt-5.6-sol; still running — gpt-6-astra; waiting another 1 minutes."), TOOL("Bash", STOP_CMD), RESULT(LINE + SUFFIX), TASKSTOP, A(LINE + SUFFIX));
const ALLOWED_TOOLS_ONLY = trace(JSON.stringify({ type: "system", tools: ["Bash", "TaskStop"] }), A(LINE + SUFFIX), TOOL("ToolSearch", { query: "select:TaskStop" }));

for (const [label, text, ok] of [
  ["assistant line before TaskStop", GOOD, true], ["line only in tool result before TaskStop", TOOL_RESULT_ONLY, false],
  ["assistant line only after TaskStop", AFTER_ONLY, false], ["no TaskStop call", NO_TASKSTOP, false], ["NOT confirmed", NOT_CONFIRMED_TRACE, false],
  ["TaskStop named only in tools list / ToolSearch", ALLOWED_TOOLS_ONLY, false],
]) check(has("timeout-stalled-stop", "stopped-at-stop", text) === ok, `stopped-at-stop: ${label} → ${ok ? "pass" : "fail"}`);

for (const [label, text, ok] of [
  ["stop report copied before TaskStop", GOOD, true], ["still-running notice before TaskStop", NOTICE_THEN_STOP, true],
  ["fields only in tool result and stop.sh arguments", TOOL_RESULT_ONLY, false], ["assistant line only after TaskStop", AFTER_ONLY, false],
  ["no TaskStop call", NO_TASKSTOP, false],
]) check(has("parallel-shared-timer", "parallel-info-before-stop", text) === ok, `parallel-info-before-stop: ${label} → ${ok ? "pass" : "fail"}`);

// tool_used graders see the JSON-encoded Bash input.
const enc = (command) => JSON.stringify({ command, description: "Run" });
const RUN_CMD = "bash '/p/skills/ask/scripts/run.sh' '/t/ask-codex/run.a' -- codex exec -s read-only --ephemeral --skip-git-repo-check --json -C '/w' -m gpt-5.6-sol -c 'model_reasoning_effort=\"high\"' --disable apps --output-schema '/p/skills/ask/consultation.schema.json' -o '/t/ask-codex/run.a/last-message.json' - < '/t/ask-codex/run.a/prompt.md' > '/t/ask-codex/run.a/events.jsonl' 2> '/t/ask-codex/run.a/stderr.log'";
check(has("timeout-stalled-stop", "used-run-script", enc(RUN_CMD)), "used-run-script: prefixed launch matches");
check(!has("timeout-stalled-stop", "used-run-script", enc(RUN_CMD.replace("bash '/p/skills/ask/scripts/run.sh' '/t/ask-codex/run.a' -- ", ""))), "used-run-script: bare codex exec does not match");
check(!has("timeout-stalled-stop", "used-run-script", enc(STOP_CMD.command)), "used-run-script: stop.sh call does not match");
check(has("timeout-stalled-stop", "used-stop-script", enc(STOP_CMD.command)), "used-stop-script: stop call matches");
check(!has("timeout-stalled-stop", "used-stop-script", enc(RUN_CMD)), "used-stop-script: run.sh call does not match");
check(has("parallel-shared-timer", "used-run-script", enc(RUN_CMD)), "parallel used-run-script: same regex");
// The CODEX_CALL regex of one-codex-exec / exec-twice must count the prefixed launch as one call and ignore the stop.
check(has("timeout-stalled-stop", "one-codex-exec", enc(RUN_CMD)), "one-codex-exec: prefixed launch counts as a codex exec");
check(!has("timeout-stalled-stop", "one-codex-exec", enc(STOP_CMD.command)), "one-codex-exec: stop.sh call is not a codex exec");
check(has("parallel-shared-timer", "two-background-runs", JSON.stringify({ command: RUN_CMD, run_in_background: true })), "two-background-runs: prefixed launch in background counts");

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
