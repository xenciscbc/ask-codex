// Offline check for the discuss skill's eval cases (spec .scratch/discuss-skill, slice S2):
//   node evals/_harness/discuss-skill-graders.test.mjs
// Every new regex grader is applied to a crafted input it must pass and one it must fail. The skill files
// are checked for the facts the graders rely on (the body marker is unique, the framing markers are unique
// to their framing, the template and framings contain none of the ids or headings a prompt grader looks for,
// so those graders only pass on what Claude filled in). The stub's canned replies are validated against
// skills/ask/discussion.schema.json and against the scaffold's files.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const evals = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repo = path.resolve(evals, "..");
const text = (...p) => fs.readFileSync(path.join(...p), "utf8").replace(/\r\n/g, "\n");
const read = (c, g) => text(evals, c, "graders", `${g}.md`);
const re = (c, g) => {
  const t = read(c, g);
  const key = /^input_match:/m.test(t) ? "input_match" : "pattern";
  return new RegExp(t.match(new RegExp(`^${key}: '((?:[^']|'')*)'$`, "m"))[1].replace(/''/g, "'"));
};
let pass = 0, fail = 0;
const expect = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const CASES = ["discuss-early-consensus", "discuss-limit-reached", "discuss-claude-first", "discuss-rounds-arg-no-question",
  "discuss-two-models-refused", "discuss-nl-not-loaded", "discuss-not-model-invocable"];
const MARKER = "<!-- ask-codex-discuss-skill-body -->";
const skill = text(repo, "skills", "discuss", "SKILL.md");
const template = text(repo, "skills", "discuss", "prompts", "discussion.md");
const round1 = text(repo, "skills", "discuss", "prompts", "framing", "round-1.md");
const roundN = text(repo, "skills", "discuss", "prompts", "framing", "round-n.md");
const askSkill = text(repo, "skills", "ask", "SKILL.md");
const schema = JSON.parse(text(repo, "skills", "ask", "discussion.schema.json"));

// --- The skill files -------------------------------------------------------------------------------
const front = skill.match(/^---\n([\s\S]*?)\n---\n/);
expect(!!front && /^name: discuss$/m.test(front[1]), "discuss SKILL.md: name is discuss");
expect(!!front && /^disable-model-invocation: true$/m.test(front[1]), "discuss SKILL.md: disable-model-invocation: true");
expect(!!front && /^description: .*\/ask-codex:discuss/m.test(front[1]), "discuss SKILL.md: the description names /ask-codex:discuss");
expect(skill.split("\n").filter((l) => l === MARKER).length === 1 && skill.split(MARKER).length === 2, "discuss SKILL.md: the marker is one line of its own, once");
const framingDir = path.join(repo, "skills", "ask", "prompts", "framing");
const others = [askSkill, text(repo, "skills", "ask", "prompts", "consultation.md"), text(repo, "skills", "review", "SKILL.md"), text(repo, "skills", "setup", "SKILL.md"), template, round1, roundN,
  ...fs.readdirSync(framingDir).map((f) => text(framingDir, f))];
expect(others.every((t) => !t.includes("ask-codex-discuss-skill-body")), "the body marker exists in no other skill or prompt file");
expect(round1.split("\n")[0] === "Discussion round: 1 (independent)." && roundN.split("\n")[0] === "Discussion round: follow-up.", "framings: the first line is the round marker");
const markerRe = { one: new RegExp(re("discuss-claude-first", "round-1-marker").source), two: new RegExp(re("discuss-early-consensus", "round-2-marker").source) };
expect(markerRe.one.test(round1) && !markerRe.one.test(roundN) && markerRe.two.test(roundN) && !markerRe.two.test(round1), "each framing carries its own marker and not the other's");
expect(!markerRe.one.test(template) && !markerRe.two.test(template), "the template carries no round marker");
for (const f of fs.readdirSync(framingDir)) {
  const t = text(framingDir, f);
  expect(!markerRe.one.test(t) && !markerRe.two.test(t), `ask's ${f} carries no discussion marker`);
}
// What the skill states, in the words the graders and the report depend on.
expect(skill.includes("`A discussion takes exactly one model: <the tokens as typed> names two.`"), "skill: the fixed two-models refusal line");
expect(re("discuss-two-models-refused", "refusal-line").test("A discussion takes exactly one model: sol, astra names two."), "the refusal grader matches the skill's line");
expect(skill.includes("`<scratch-directory>/claude-round-1.md`") && /before any `prepare`, `run` or other Codex command/.test(skill), "skill: Claude's round-1 file has a fixed basename and is written before any Codex command");
expect(/with the Write tool/.test(skill) && /never rewrite or edit this file/.test(skill), "skill: the file is written with the Write tool and not rewritten");
expect(skill.includes('`reply_schema` with the value `"discussion"`'), "skill: every request carries reply_schema discussion");
expect(/never resume or fork/.test(skill), "skill: a fresh Codex session every round");
expect(/Resolve once\./.test(skill) && /Never resolve again/.test(skill), "skill: the model is resolved once");
expect(/rounds <n>/.test(skill) && /3 \(default; no round count given\)/.test(skill), "skill: rounds <n>, default 3 disclosed");
for (const h of ["## Discussion process", "## Agreed", "## For you to decide"]) expect(skill.includes(`\`${h}\``), `skill: the report heading ${h}`);
expect(skill.indexOf("`## Discussion process`") < skill.indexOf("`## Agreed`") && skill.indexOf("`## Agreed`") < skill.indexOf("`## For you to decide`"), "skill: the headings are listed in order");
expect(skill.includes("`Claude recommends: <recommendation> — <reason>`") && skill.includes("`Codex recommends: <recommendation> — <reason>`"), "skill: the two recommendation lines");
expect(/ONE closing message/.test(skill) && /delete every temporary file/.test(skill), "skill: order of work ends in one closing message after the cleanup");
expect(/Tentative agreements \(locked\):/.test(skill) && /Contested points:/.test(skill), "skill: the carried-points headings the round-1 grader looks for");
expect(/^<!-- ask-codex-discuss-skill-body -->$/m.test(skill) && !/^\s*Contested points:/m.test(template + round1), "template and round-1 framing never use the carried-points headings");
expect(!/"trigger"/.test(skill), "skill: the request file gains no trigger field");
// The ask pointer line: exactly one line, and it names the command.
const pointer = askSkill.split("\n").filter((l) => l.includes("/ask-codex:discuss"));
expect(pointer.length === 1 && /not an `ask` type/.test(pointer[0]) && /cannot invoke it/.test(pointer[0]), "ask SKILL.md: one pointer line to /ask-codex:discuss");
expect(askSkill.split("\n").filter((l) => l.includes("/ask-codex:review")).length === 1, "ask SKILL.md: the review pointer is unchanged");
const plugin = JSON.parse(text(repo, ".claude-plugin", "plugin.json"));
expect(["ask", "setup", "review", "discuss"].every((s) => plugin.skills.includes(`./skills/${s}`)), "plugin.json lists the discuss skill and the others");

// --- Prompts as Claude fills them ---------------------------------------------------------------------------
const fill = (framing, q, ctx) => template.replace("{{framing}}", framing).replace("{{question}}", q).replace("{{context}}", ctx).replace("{{extra_paths_or_none}}", "none");
const bare1 = fill(round1, "", "");
const bareN = fill(roundN, "", "");
for (const w of [/\bL\d+\b/, /\bC[123]\b/, /Contested points:/, /Tentative agreements \(locked\)/, /Without a shared store/, /src\/login\.js/, /docs\/constraints\.md/]) {
  expect(!w.test(bare1) && !w.test(bareN), `template + framing alone do not contain ${w}`);
}
const TOPIC = "design rate limiting for login() in src/login.js; the constraints are in docs/constraints.md";
const R3 = JSON.parse(text(evals, "discuss-early-consensus", "scaffold.sh").match(/cat > \.stub\/scenario\.json <<'EOF'\n([\s\S]*?)\nEOF\n/)[1]).exec.sequence[0].reply.points[2].reason;
const PROMPT1 = fill(round1, TOPIC, `Where to look: src/login.js, docs/constraints.md.\nRequirement: limit password guessing on login().`);
const PROMPT2 = fill(roundN, 'Respond to the contested points under "Context from Claude".',
  `Topic: ${TOPIC}\nRound: 2 of at most 5\nTentative agreements (locked):\n- L2 = C1: Count failed attempts per username and per IP.\n- L3 = C2: Return one error text.\nContested points:\n- C3 (raised by Codex)\n  Statement: Keep the failure counters in a shared Redis instance.\n  Reason: ${R3}\n  Evidence: src/login.js:3\n  Claude's position: disputed — docs/constraints.md:3 forbids Redis.\n  Codex's position: raised.\n- L1 (raised by Claude)\n  Statement: Reset the counter after a success.\n  Reason: A user who logs in is not an attacker.\n  Evidence: none\n  Claude's position: raised.\n  Codex's position: not yet answered.`);

// --- Call counts from the stub sentinel -------------------------------------------------------------------------
const TS = "2026-10-04T03:04:05.123456+00:00\n";
for (const c of ["discuss-early-consensus", "discuss-limit-reached"]) {
  const two = re(c, "two-calls");
  expect(/path: \.stub\/exec\.sentinel/.test(read(c, "two-calls")), `${c}/two-calls reads the stub sentinel`);
  expect(two.test(TS + TS) && two.test(TS + TS.trim()) && two.test((TS + TS).replace(/\n/g, "\r\n")), `${c}/two-calls: two lines pass`);
  expect(!two.test(TS) && !two.test(TS + TS + TS) && !two.test(""), `${c}/two-calls: one, three or no lines fail`);
}
const has = re("discuss-claude-first", "has-call");
expect(has.test(TS) && !has.test(""), "discuss-claude-first/has-call: one call passes, none fails");
expect(re("discuss-rounds-arg-no-question", "has-call").test(TS + TS) && !re("discuss-rounds-arg-no-question", "has-call").test(""), "discuss-rounds-arg-no-question/has-call: a call passes, none fails");
const most = re("discuss-nl-not-loaded", "at-most-one-call");
expect(most.test("") && most.test(TS) && !most.test(TS + TS), "discuss-nl-not-loaded/at-most-one-call: zero or one passes, two fail");
for (const c of ["discuss-two-models-refused", "discuss-not-model-invocable"]) {
  const g = read(c, "no-exec-sentinel");
  expect(/^type: file_exists$/m.test(g) && /^path: \.stub\/exec\.sentinel$/m.test(g) && /^exists: false$/m.test(g), `${c}/no-exec-sentinel: zero calls = no sentinel file`);
  expect(!/exec\.sentinel/.test(text(evals, c, "scaffold.sh")), `${c}: the scaffold does not create the sentinel`);
}
for (const c of ["discuss-early-consensus", "discuss-limit-reached", "discuss-claude-first", "discuss-rounds-arg-no-question"]) {
  expect(!/exec\.sentinel|exec-stdin|exec-argv/.test(text(evals, c, "scaffold.sh").replace(/^#.*$/gm, "")), `${c}: the scaffold leaves the stub records to the stub`);
}
const nlScaffold = text(evals, "discuss-nl-not-loaded", "scaffold.sh");
expect(/^: > \.stub\/exec-stdin\.txt$/m.test(nlScaffold) && /^: > \.stub\/exec\.sentinel$/m.test(nlScaffold), "discuss-nl-not-loaded: the scaffold creates both records empty (a regex grader fails on a missing file)");

// --- Per-round records ------------------------------------------------------------------------------------------------
const argv = (schemaName) => JSON.stringify(["exec", "-s", "read-only", "--ephemeral", "--output-schema", `/mnt/d/x/ask-codex/skills/ask/${schemaName}`, "-o", "/tmp/o", "-"], null, 2);
for (const [c, n] of [["discuss-early-consensus", 1], ["discuss-early-consensus", 2]]) {
  const g = read(c, `schema-round-${n}`);
  const r = re(c, `schema-round-${n}`);
  expect(new RegExp(`path: \\.stub/exec-argv\\.${n}\\.json`).test(g), `${c}/schema-round-${n} reads exec-argv.${n}.json`);
  expect(r.test(argv("discussion.schema.json")) && !r.test(argv("consultation.schema.json")) && !r.test(argv("my-discussion.schema.json.bak")), `${c}/schema-round-${n}: only the discussion schema passes`);
}
expect(/path: \.stub\/exec-stdin\.2\.txt/.test(read("discuss-early-consensus", "round-2-marker")), "round-2-marker reads exec-stdin.2.txt");
expect(re("discuss-early-consensus", "round-2-marker").test(PROMPT2) && !re("discuss-early-consensus", "round-2-marker").test(PROMPT1), "round-2-marker: a round-n prompt passes, a round-1 prompt fails");
expect(re("discuss-limit-reached", "round-2-marker").test(PROMPT2) && !re("discuss-limit-reached", "round-2-marker").test(PROMPT1), "discuss-limit-reached/round-2-marker: a round-n prompt passes, a round-1 prompt fails");
const ids = re("discuss-early-consensus", "round-2-ids");
expect(ids.test(PROMPT2) && !ids.test(PROMPT1) && !ids.test(PROMPT2.replace("C3 (raised", "C9 (raised").replace(/\bC3\b/g, "C9")) && !ids.test(PROMPT2.replace(/\bL1\b/g, "L9")), "round-2-ids: all of L1, C1, C2, C3 pass; a missing one or a round-1 prompt fails");
expect(!ids.test(bareN) && !ids.test(bare1), "round-2-ids: the bare template and framing do not satisfy it");
const verb = re("discuss-early-consensus", "round-2-reason-verbatim");
expect(verb.test(PROMPT2.replace("Without a shared store", "without a shared store")), "round-2-reason-verbatim: a lower-case first letter passes (seen in a t02 trace)");
expect(verb.test(PROMPT2) && !verb.test(PROMPT2.replace("shared store", "shared service")) && !verb.test(PROMPT2.replace(R3, R3.split(" ").slice(0, 8).join(" "))) && !verb.test(bareN), "round-2-reason-verbatim: the verbatim reason passes; a reworded or shortened one fails");
expect(re("discuss-claude-first", "round-1-marker").test(PROMPT1) && !re("discuss-claude-first", "round-1-marker").test(PROMPT2), "round-1-marker: a round-1 prompt passes, a round-n prompt fails");
const notN = re("discuss-claude-first", "round-1-not-round-n");
expect(/^match: not_contains$/m.test(read("discuss-claude-first", "round-1-not-round-n")) && !notN.test(PROMPT1) && notN.test(PROMPT2), "round-1-not-round-n: a round-n prompt fails");
const carried = re("discuss-claude-first", "round-1-no-carried-points");
expect(/^match: not_contains$/m.test(read("discuss-claude-first", "round-1-no-carried-points")) && !carried.test(PROMPT1) && carried.test(PROMPT2) && carried.test(PROMPT1 + "\nContested points: none") && carried.test(PROMPT1 + "\nTentative agreements (locked):"), "round-1-no-carried-points: either heading fails a round-1 prompt");
const blind = re("discuss-claude-first", "round-1-blind");
expect(/^match: not_contains$/m.test(read("discuss-claude-first", "round-1-blind")) && !blind.test(PROMPT1) && blind.test(PROMPT1 + "\nClaude's point L2: use a lockout") && blind.test(PROMPT2), "round-1-blind: a Claude point id in the prompt fails");
for (const g of ["round-1-marker", "round-1-not-round-n", "round-1-no-carried-points", "round-1-blind"]) {
  expect(/path: \.stub\/exec-stdin\.1\.txt/.test(read("discuss-claude-first", g)), `discuss-claude-first/${g} reads exec-stdin.1.txt`);
}

// --- Order in the trace ------------------------------------------------------------------------------------------------
const A = (t) => JSON.stringify({ type: "assistant", message: { role: "assistant", content: [{ type: "text", text: t }] } });
const TOOL = (name, input) => JSON.stringify({ type: "assistant", message: { role: "assistant", content: [{ type: "tool_use", id: "toolu_x", name, input }] } });
const RESULT = (content) => JSON.stringify({ type: "user", message: { role: "user", content: [{ type: "tool_result", tool_use_id: "x", content }] } });
const trace = (...l) => l.join("\n") + "\n";
const CF = "/tmp/claude-eval-x/scratch/claude-round-1.md";
const RUN = TOOL("Bash", { command: "python '/mnt/d/x/ask-codex/skills/ask/scripts/consult.py' run '/tmp/ask-codex/run.abc123'", description: "Run round 1" });
const RESOLVE = TOOL("Bash", { command: "python '/mnt/d/x/ask-codex/skills/ask/scripts/consult.py' resolve '/tmp/s/resolve.json'" });
const PREPARE = TOOL("Bash", { command: "python '/mnt/d/x/ask-codex/skills/ask/scripts/consult.py' prepare '/tmp/s/request-round-1.json' --base '/tmp/s'" });
const WRITE_CF = TOOL("Write", { file_path: CF, content: "L1: statement ..." });
const WRITE_REQ = TOOL("Write", { file_path: "/tmp/s/request-round-1.json", content: "{}" });
const SKILL_TEXT = RESULT("Launch with: python '<skill>/scripts/consult.py' run '<directory>'");
const first = re("discuss-claude-first", "claude-file-before-run");
expect(/^target: trace$/m.test(read("discuss-claude-first", "claude-file-before-run")), "claude-file-before-run grades the trace");
expect(first.test(trace(RESOLVE, WRITE_CF, PREPARE, WRITE_REQ, RUN)), "claude-file-before-run: resolve, file, prepare, run passes");
expect(first.test(trace(A("Reading the ask skill"), SKILL_TEXT, TOOL("Read", { file_path: "/x/y.js" }), WRITE_CF, RUN)), "claude-file-before-run: a skill text that mentions run before the Write does not break it");
expect(!first.test(trace(RESOLVE, WRITE_REQ, PREPARE, RUN, WRITE_CF)), "claude-file-before-run: the file written after run fails");
expect(!first.test(trace(RESOLVE, WRITE_REQ, RUN)), "claude-file-before-run: no round-1 file at all fails");
expect(!first.test(trace(RESOLVE, TOOL("Write", { file_path: "/tmp/s/claude-round-2.md", content: "x" }), RUN)), "claude-file-before-run: another file name fails");
expect(!first.test(trace(RESOLVE, TOOL("Bash", { command: "echo claude-round-1.md > /tmp/x" }), RUN)), "claude-file-before-run: a Bash command naming the file is not the Write");
expect(!first.test(trace(A("I will write claude-round-1.md"), RUN, WRITE_CF)), "claude-file-before-run: text naming the file does not stand in for the Write");
const deleted = re("discuss-early-consensus", "temp-file-deleted");
const RM = TOOL("Bash", { command: `rm -f '${CF}' '/tmp/s/resolve.json'`, description: "Delete temporary files" });
expect(deleted.test(trace(WRITE_CF, RUN, RM)), "temp-file-deleted: write, run, rm passes");
expect(deleted.test(trace(WRITE_CF, RUN, TOOL("Bash", { command: `ls -la '/tmp/s/'\nrm -f '${CF}'\nls -la '/tmp/s/'` }))), "temp-file-deleted: an rm on a later line of a multi-line command passes (seen in a t02 trace)");
expect(!deleted.test(trace(WRITE_CF, RUN, TOOL("Bash", { command: `ls -la '/tmp/s/'\nfirm '${CF}'` }))), "temp-file-deleted: a word merely ending in rm does not count");
expect(!deleted.test(trace(WRITE_CF, RUN)) && !deleted.test(trace(RM, WRITE_CF, RUN)) && !deleted.test(trace(WRITE_CF, RUN, TOOL("Bash", { command: "rm -f '/tmp/s/resolve.json'" }))), "temp-file-deleted: no rm, an rm before the Write, or an rm of another file fails");

// --- The report --------------------------------------------------------------------------------------------------------
const REPORT = [
  "## Discussion process", "Topic: rate limiting for login()", "Model: gpt-6-sol (high)", "Round limit: 2", "MCP policy: all MCP servers disabled",
  "Round 1: C1 and C2 matched my L2 and L3; C3 (shared Redis) disputed by me against docs/constraints.md:3.",
  "Round 2: Codex maintained C3 (a second instance later); I maintained my objection.",
  "", "## Agreed", "- L2 = C1: Count failed attempts per username and per IP.", "- L3 = C2: Return one error text.",
  "", "## For you to decide", "- C3 — Keep the failure counters in a shared Redis instance.",
  "  Claude recommends: in-process counters — docs/constraints.md:3 forbids Redis.",
  "  Codex recommends: a shared store — a later second instance would lose the limit.",
].join("\n");
const sect = re("discuss-early-consensus", "report-sections");
expect(sect.test(REPORT) && sect.test(REPORT.replace(/^## (.*)$/gm, "**$1**")) && sect.test(REPORT.replace(/^## (.*)$/gm, "### $1:")), "report-sections: the three headings in order pass, plain or marked up");
expect(!sect.test(REPORT.replace("## For you to decide", "## Open items")) && !sect.test(REPORT.replace("## Agreed", "## Agreements")) && !sect.test(REPORT.replace("## Discussion process", "## Process")), "report-sections: a renamed heading fails");
const order = ["## Discussion process", "## Agreed", "## For you to decide"];
expect(!sect.test([order[1], "x", order[0], "x", order[2], "x"].join("\n")) && !sect.test("The topic was discussed. Agreed on most. For you to decide: C3."), "report-sections: wrong order or free prose fails");
expect(sect.source === re("discuss-limit-reached", "report-sections").source, "the report-sections grader is the same in both cases");
const dec = re("discuss-limit-reached", "c3-decision-item");
expect(dec.test(REPORT) && dec.test(REPORT.replace(/Claude recommends:/, "**Claude recommends:**").replace(/Codex recommends:/, "**Codex recommends**:")), "c3-decision-item: C3 with both recommendation lines passes");
expect(!dec.test(REPORT.replace(/\n  Codex recommends:[^\n]*/, "")), "c3-decision-item: a missing Codex recommends line fails");
expect(!dec.test(REPORT.replace(/\n  Claude recommends:[^\n]*/, "")), "c3-decision-item: a missing Claude recommends line fails");
expect(!dec.test(REPORT.replace("- C3 — Keep", "- C4 — Keep")), "c3-decision-item: C3 not among the decision items fails");
const agreedOnly = REPORT.replace("- L3 = C2:", "- L3 = C3:").replace("- C3 — Keep the failure counters in a shared Redis instance.", "- L9 — Reset the counter after a success.");
expect(!dec.test(agreedOnly), "c3-decision-item: C3 only under Agreed fails");
expect(!dec.test(REPORT.replace("- C3 — Keep the failure counters in a shared Redis instance.\n", "- C3 — Keep the counters.\n- C1 — Another item.\n")), "c3-decision-item: another C id between C3 and the recommendation lines fails");
expect(/^type: regex$/m.test(read("discuss-limit-reached", "c3-decision-item")) && !/^target:/m.test(read("discuss-limit-reached", "c3-decision-item")), "c3-decision-item and report-sections grade the final response");

// --- The two-model refusal and the other tool graders --------------------------------------------------------------------
const rej = re("discuss-two-models-refused", "refusal-line");
expect(rej.test("A discussion takes exactly one model: sol, astra names two.") && rej.test("**A discussion takes exactly one model:** `sol, astra` names two.") && !rej.test("Parallel consultation takes at most two different models.") && !rej.test("I cannot start that."), "refusal-line: only the fixed line passes");
const cmd = (s) => JSON.stringify({ command: s, description: "x" });
const cd = re("discuss-early-consensus", "no-bare-cd");
expect(cd.test(cmd("cd /w && ls")) && !cd.test(cmd("ls /w")) && !cd.test(cmd("python3 --version")), "no-bare-cd: a cd command is caught");
const codex = re("discuss-two-models-refused", "no-codex-call");
expect(codex.test(cmd("codex exec -s read-only -")) && codex.test(cmd("/usr/bin/codex mcp list")) && !codex.test(cmd("python '/x/consult.py' resolve '/tmp/r.json'")), "no-codex-call: a direct codex exec or mcp call is caught; the script is not");
for (const c of CASES) {
  const g = read(c, "no-bare-cd");
  expect(/^type: tool_used$/m.test(g) && /^tool: Bash$/m.test(g) && /^max: 0$/m.test(g), `${c}/no-bare-cd allows none`);
}
for (const c of ["discuss-early-consensus", "discuss-limit-reached", "discuss-claude-first", "discuss-rounds-arg-no-question"]) {
  const g = read(c, "no-violations");
  expect(/^match: not_contains$/m.test(g) && /path: \.stub\/violations\.log/.test(g) && /^pattern: '\\S'$/m.test(g), `${c}/no-violations is the usual stub check`);
}
const ask = read("discuss-rounds-arg-no-question", "no-ask-user-question");
expect(/^type: tool_used$/m.test(ask) && /^tool: AskUserQuestion$/m.test(ask) && /^min: 0$/m.test(ask) && /^max: 0$/m.test(ask), "discuss-rounds-arg-no-question: no AskUserQuestion use");
expect(/allowed_tools: \[[^\]]*AskUserQuestion/.test(text(evals, "discuss-rounds-arg-no-question", "prompt.md")), "discuss-rounds-arg-no-question: the tool is available, so its absence means something");
expect(/rounds 2/.test(text(evals, "discuss-rounds-arg-no-question", "prompt.md").split(/\n---\n/).pop()), "discuss-rounds-arg-no-question: the command carries rounds 2");

// --- The skill-body marker in the trace ---------------------------------------------------------------------------------------
const traceLine = (t) => JSON.stringify({ type: "user", message: { role: "user", content: [{ type: "text", text: t }] } });
const loaded = [
  TOOL("Skill", { skill: "ask-codex:discuss" }),
  RESULT("Launching skill: ask-codex:discuss"),
  traceLine("Base directory for this skill: /mnt/d/x/ask-codex/skills/discuss\n\n" + skill.replace(/^---\n[\s\S]*?\n---\n/, "").replace(/\n/g, "\r\n")),
].join("\n");
const askLoaded = traceLine("Base directory for this skill: /mnt/d/x/ask-codex/skills/ask\n\n" + askSkill.replace(/^---\n[\s\S]*?\n---\n/, ""));
for (const c of ["discuss-nl-not-loaded", "discuss-not-model-invocable"]) {
  const body = re(c, "no-skill-body");
  const g = read(c, "no-skill-body");
  expect(/^target: trace$/m.test(g) && /^match: not_contains$/m.test(g), `${c}/no-skill-body is a not_contains grader on the trace`);
  expect(body.test(loaded), `${c}/no-skill-body: a Skill-tool load of the discuss body is found (the run fails)`);
  expect(!body.test(askLoaded), `${c}/no-skill-body: loading ask (with its pointer line) is clean`);
  expect(!body.test(traceLine("Run /ask-codex:discuss yourself; I cannot start it.")), `${c}/no-skill-body: naming the command is clean`);
}
const nfs = re("discuss-nl-not-loaded", "no-discussion-framing-sent");
expect(/^match: not_contains$/m.test(read("discuss-nl-not-loaded", "no-discussion-framing-sent")) && nfs.test(PROMPT1) && nfs.test(PROMPT2) && !nfs.test("Consultation type: second opinion.") && !nfs.test(""), "discuss-nl-not-loaded/no-discussion-framing-sent: a discussion prompt of either round fails; an ask prompt or the empty file passes");
expect(/path: \.stub\/exec-stdin\.txt/.test(read("discuss-nl-not-loaded", "no-discussion-framing-sent")), "no-discussion-framing-sent reads exec-stdin.txt");
const names = re("discuss-nl-not-loaded", "names-command");
expect(names.test("A multi-round discussion is `/ask-codex:discuss` — type it to start one.") && !names.test("I can't run that skill.") && !names.test("Use /ask-codex:review"), "discuss-nl-not-loaded/names-command: the reply must name the command");
const prompt = (c) => text(evals, c, "prompt.md");
const userMessage = (c) => prompt(c).split(/\n---\n/).pop().trim();
expect(/run \/ask-codex:discuss/.test(text(evals, "discuss-not-model-invocable", "scaffold.sh")) && !/ask-codex|discuss|Codex/i.test(userMessage("discuss-not-model-invocable")), "discuss-not-model-invocable: only a file the task reads asks for the discussion; the user's message does not");
expect(/^runs: 5$/m.test(prompt("discuss-nl-not-loaded")) && /^runs: 5$/m.test(prompt("discuss-not-model-invocable")), "both negative cases run 5 times");
expect(/^discuss with Codex over a few rounds .*src\/login\.js.*docs\/constraints\.md/.test(userMessage("discuss-nl-not-loaded")) && !userMessage("discuss-nl-not-loaded").includes("/ask-codex"), "discuss-nl-not-loaded: the user's own words name a concrete topic in the scaffold, no slash command");
expect(userMessage("discuss-two-models-refused").startsWith("/ask-codex:discuss sol, astra "), "discuss-two-models-refused: two comma-separated model tokens");
for (const c of ["discuss-early-consensus", "discuss-limit-reached", "discuss-claude-first", "discuss-rounds-arg-no-question"]) {
  expect(userMessage(c).startsWith("/ask-codex:discuss rounds "), `${c}: a typed command with rounds`);
}
expect(userMessage("discuss-early-consensus").startsWith("/ask-codex:discuss rounds 5 ") && userMessage("discuss-limit-reached").startsWith("/ask-codex:discuss rounds 2 "), "early-consensus uses rounds 5, limit-reached rounds 2");

// --- Validate a reply against the discussion schema (the node types the schema uses) --------------------------------------------
const valid = (v, s, where, errors) => {
  const types = [].concat(s.type ?? []);
  const kind = v === null ? "null" : Array.isArray(v) ? "array" : typeof v === "number" ? (Number.isInteger(v) ? "integer" : "number") : typeof v;
  if (types.length && !types.includes(kind)) errors.push(`${where}: ${kind} is not ${types}`);
  if (s.enum && !s.enum.includes(v)) errors.push(`${where}: ${JSON.stringify(v)} not in enum`);
  if (kind === "object" && s.properties) {
    for (const k of s.required || []) if (!(k in v)) errors.push(`${where}: missing ${k}`);
    for (const k of Object.keys(v)) { if (!(k in s.properties)) errors.push(`${where}: extra ${k}`); else valid(v[k], s.properties[k], `${where}.${k}`, errors); }
  }
  if (kind === "array" && s.items) v.forEach((x, i) => valid(x, s.items, `${where}[${i}]`, errors));
};
const checkErr = (r) => { const e = []; valid(r, schema, "reply", e); return e; };

// --- Every case: slash commands, graders on the right records, stub replies that fit the files -------------------------------------
const RECORDS = new Set([".stub/exec.sentinel", ".stub/exec-stdin.txt", ".stub/violations.log", ...[1, 2].flatMap((n) => [`.stub/exec-stdin.${n}.txt`, `.stub/exec-argv.${n}.json`])]);
for (const c of CASES) {
  for (const f of ["case.yaml", "prompt.md", "scaffold.sh"]) expect(fs.existsSync(path.join(evals, c, f)), `${c}/${f} exists`);
  expect(new RegExp(`^name: ${c}$`, "m").test(text(evals, c, "case.yaml")), `${c}: case.yaml names the case`);
  expect(/^description: ".+"$/m.test(prompt(c)) && /^max_turns: \d+$/m.test(prompt(c)) && /^timeout_seconds: \d+$/m.test(prompt(c)) && /^allowed_tools: \[.*\]$/m.test(prompt(c)), `${c}: prompt.md has description, max_turns, timeout_seconds and allowed_tools`);
  if (!/^runs: 5$/m.test(prompt(c))) expect(!/^runs:/m.test(prompt(c)), `${c}: no runs override (the other cases run at the harness default)`);
  for (const g of fs.readdirSync(path.join(evals, c, "graders"))) {
    const t = read(c, g.replace(/\.md$/, ""));
    expect(!/exec-calls/.test(t), `${c}/${g}: never grades exec-calls/*.json`);
    expect(!/^type: tool_used$/m.test(t) || /^tool: (?:Bash|AskUserQuestion)$/m.test(t), `${c}/${g}: no Skill-tool grader for a user-only skill`);
    if (/^pattern:|^input_match:/m.test(t)) expect((() => { try { re(c, g.replace(/\.md$/, "")); return true; } catch { return false; } })(), `${c}/${g}: the pattern compiles as a JavaScript regex`);
    expect(!/\(\?i\)/.test(t), `${c}/${g}: no inline flags`);
    const p = t.match(/^  path: (.+)$/m) || t.match(/^path: (.+)$/m);
    if (p) expect(RECORDS.has(p[1].trim()), `${c}/${g}: reads a record the stub writes (${p[1]})`);
  }
  const s = text(evals, c, "scaffold.sh");
  expect(/^set -euo pipefail$/m.test(s), `${c}: the scaffold stops on error`);
  const scen = s.match(/cat > \.stub\/scenario\.json <<'EOF'\n([\s\S]*?)\nEOF\n/);
  expect(!!scen, `${c}: the scaffold writes a stub scenario`);
  if (!scen) continue;
  const exec = JSON.parse(scen[1]).exec;
  const files = {};
  for (const m of s.matchAll(/cat > (\S+) <<'EOF'\n([\s\S]*?)\nEOF\n/g)) files[m[1]] = m[2].split("\n");
  const replies = exec.sequence ? exec.sequence.map((e) => e.reply) : [];
  if (exec.sequence) expect(replies.length === 2, `${c}: the sequence has one entry per round the case needs`);
  for (const [i, r] of replies.entries()) {
    const errors = checkErr(r);
    expect(errors.length === 0, `${c}: round ${i + 1} reply fits discussion.schema.json ${errors.slice(0, 3)}`);
    for (const p of r.points) {
      for (const ev of p.evidence) {
        const [, file, line] = ev.match(/^(.+):(\d+)$/);
        expect(!!files[file] && (files[file][Number(line) - 1] || "").trim() !== "", `${c} round ${i + 1} ${p.id}: evidence ${ev} points at a line the scaffold wrote`);
      }
    }
  }
  if (replies.length) {
    const [r1, r2] = replies;
    expect(r1.points.every((p) => /^C\d+$/.test(p.id) && p.stance === null), `${c}: round 1 raises only new C points with a null stance`);
    const want = ["C1", "C2", "C3", ...Array.from({ length: 12 }, (_, k) => `L${k + 1}`)];
    expect(JSON.stringify(r2.points.map((p) => p.id)) === JSON.stringify(want), `${c}: round 2 answers C1-C3 and L1-L12`);
    expect(r2.points.every((p) => ["accept", "maintain", "revise"].includes(p.stance)), `${c}: every round-2 point has a stance`);
    expect(r1.points[2].reason === R3 && R3.length > 40, `${c}: C3's reason is the string the verbatim grader looks for`);
    const c3 = r2.points.find((p) => p.id === "C3");
    const wantStance = c === "discuss-early-consensus" ? "accept" : "maintain";
    expect(c3.stance === wantStance, `${c}: round 2 ${wantStance}s C3`);
    expect(r2.points.filter((p) => p.stance === "maintain").length === (wantStance === "maintain" ? 1 : 0), `${c}: ${wantStance === "accept" ? "nothing" : "only C3"} is maintained in round 2`);
    // C3 contradicts the constraints file in the scaffold, so Claude disputes it.
    expect(/No Redis/.test(s) && /Redis/.test(r1.points[2].statement), `${c}: C3 (a shared Redis) contradicts the constraints file`);
  }
}
// The schema checker bites: a reply with a wrong type, a missing key and an extra key is refused.
{
  const good = JSON.parse(text(evals, "discuss-limit-reached", "scaffold.sh").match(/cat > \.stub\/scenario\.json <<'EOF'\n([\s\S]*?)\nEOF\n/)[1]).exec.sequence[1].reply;
  const bad = (f) => { const r = JSON.parse(JSON.stringify(good)); f(r); return checkErr(r).length > 0; };
  expect(checkErr(good).length === 0, "schema checker: the stub's round-2 reply is valid");
  expect(bad((r) => { r.points[0].user_call = "false"; }) && bad((r) => { delete r.points[0].reopen; }) && bad((r) => { r.points[0].extra = 1; }) && bad((r) => { r.points[0].stance = "agree"; }), "schema checker: a string boolean, a missing key, an extra key and an unknown stance are refused");
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
