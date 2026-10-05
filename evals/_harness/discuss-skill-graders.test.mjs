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
  "discuss-two-models-refused", "discuss-nl-not-loaded", "discuss-not-model-invocable", "discuss-headless-default", "discuss-rounds-out-of-range"];
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
const early = re("discuss-early-consensus", "stops-early");
expect(/path: \.stub\/exec\.sentinel/.test(read("discuss-early-consensus", "stops-early")), "discuss-early-consensus/stops-early reads the stub sentinel");
expect(early.test(TS + TS) && early.test(TS + TS + TS) && early.test((TS + TS + TS).replace(/\n/g, "\r\n")) && early.test(TS + TS.trim()), "discuss-early-consensus/stops-early: two or three lines pass");
expect(!early.test(TS) && !early.test(TS + TS + TS + TS) && !early.test(TS.repeat(5)) && !early.test(""), "discuss-early-consensus/stops-early: one, four, five (the limit) or no lines fail");
for (const c of ["discuss-limit-reached"]) {
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
for (const c of ["discuss-two-models-refused", "discuss-not-model-invocable", "discuss-rounds-out-of-range"]) {
  const g = read(c, "no-exec-sentinel");
  expect(/^type: file_exists$/m.test(g) && /^path: \.stub\/exec\.sentinel$/m.test(g) && /^exists: false$/m.test(g), `${c}/no-exec-sentinel: zero calls = no sentinel file`);
  expect(!/exec\.sentinel/.test(text(evals, c, "scaffold.sh")), `${c}: the scaffold does not create the sentinel`);
}
for (const c of ["discuss-early-consensus", "discuss-limit-reached", "discuss-claude-first", "discuss-rounds-arg-no-question", "discuss-headless-default"]) {
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
expect(dec.test(REPORT.replace("docs/constraints.md:3 forbids Redis.", "docs/constraints.md:3 forbids Redis; Codex maintained C3 while accepting L1.")), "c3-decision-item: C3 named again inside its own recommendation passes (seen in a t02b reply)");
expect(!dec.test(REPORT.replace("docs/constraints.md:3 forbids Redis.", "see C1.")), "c3-decision-item: another C id inside the recommendations still fails");
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
for (const c of ["discuss-early-consensus", "discuss-limit-reached", "discuss-claude-first", "discuss-rounds-arg-no-question", "discuss-headless-default"]) {
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
    expect(!/^type: tool_used$/m.test(t) || /^tool: (?:Bash|AskUserQuestion|Write)$/m.test(t), `${c}/${g}: no Skill-tool grader for a user-only skill`);
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
  if (exec.sequence) expect(replies.length === (c === "discuss-headless-default" ? 3 : 2), `${c}: the sequence has one entry per round the case needs`);
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
    if (c === "discuss-headless-default") {
      const p3 = replies[2].points[0];
      expect(replies[2].points.length === 1 && p3.id === "C3" && p3.stance === "maintain" && p3.evidence.every((ev) => !!files[ev.split(":")[0]]), `${c}: round 3 maintains only C3, so the discussion stops at the default limit`);
    }
    expect(c3.stance === wantStance, `${c}: round 2 ${wantStance}s C3`);
    expect(r2.points.filter((p) => p.stance === "maintain").length === (wantStance === "maintain" ? 1 : 0), `${c}: ${wantStance === "accept" ? "nothing" : "only C3"} is maintained in round 2`);
    // C3 contradicts the constraints file in the scaffold, so Claude disputes it.
    expect(/No Redis/.test(s) && /Redis/.test(r1.points[2].statement), `${c}: C3 (a shared Redis) contradicts the constraints file`);
  }
}
// --- Ticket 03: the round limit question, the headless default and the out-of-range refusal ---------------------------------------
{
  const sec = skill.slice(skill.indexOf("## 2. Round limit"), skill.indexOf("## 3. Model"));
  expect(sec.includes("`AskUserQuestion`") && /exactly the options `3`, `5` and `7`/.test(sec), "skill section 2: the AskUserQuestion question offers exactly 3, 5 and 7");
  expect(/whole number from 2 to 10/.test(sec) && /same question again/.test(sec), "skill section 2: a custom answer must be 2 to 10, otherwise asked again");
  expect(/never ask in text/.test(sec) && /cannot be loaded or its call fails/.test(sec), "skill section 2: headless means absent, failing or unloadable, and never asks in text");
  expect(sec.includes("`3 (default; no round count given)`") && /Headless: the limit is 3 and nothing is asked/.test(sec), "skill section 2: headless without rounds uses 3 and discloses it");
  expect(sec.includes("`Round limit rejected: <value as typed> — a discussion needs 2 to 10 rounds.`") && /before any Codex command and before creating any file/.test(sec), "skill section 2: headless out-of-range keeps the fixed refusal line and stops before any command or file");
  expect(/state the allowed range/.test(sec) && /Only the user's own answer/.test(sec), "skill section 2: interactive out-of-range states the range and asks; only the user's answer sets the limit");
  expect(/^2\. Fix the round limit\.\n3\. Resolve the model\./m.test(skill), "skill: the round limit comes before the model");
  const three = re("discuss-headless-default", "three-calls");
  expect(/path: \.stub\/exec\.sentinel/.test(read("discuss-headless-default", "three-calls")), "discuss-headless-default/three-calls reads the stub sentinel");
  expect(three.test(TS + TS + TS) && three.test(TS + TS + TS.trim()) && three.test((TS + TS + TS).replace(/\n/g, "\r\n")), "discuss-headless-default/three-calls: three lines pass");
  expect(!three.test(TS + TS) && !three.test(TS + TS + TS + TS) && !three.test(TS) && !three.test(""), "discuss-headless-default/three-calls: two, four, one or no lines fail");
  const disc = re("discuss-headless-default", "default-disclosed");
  expect(disc.test("Round limit: 3 (default; no round count given)") && disc.test("**Round limit:** 3 (default; no round count given)") && disc.test(REPORT.replace("Round limit: 2", "Round limit: 3 (default; no round count given)")), "default-disclosed: the fixed wording passes, plain or marked up");
  expect(disc.test("Round limit: 3 (default; no round count given — no interactive question tool was available in this session, so the headless default applied)"), "default-disclosed: a clause added inside the parentheses passes (seen in a t03 reply)");
  expect(!disc.test("Round limit: 3 (default; no round count\ngiven)") && !disc.test("Round limit: 3 (default; no rounds)"), "default-disclosed: the fixed words still must appear unbroken");
  expect(!disc.test(REPORT.replace("Round limit: 2", "Round limit: 3")) && !disc.test("Round limit: 5 (default; no round count given)") && !disc.test("Round limit: 3 (you chose it)") && !disc.test(""), "default-disclosed: a bare 3, another number or other wording fails");
  const rej1 = re("discuss-rounds-out-of-range", "refusal-line");
  expect(rej1.test("Round limit rejected: 1 — a discussion needs 2 to 10 rounds.") && rej1.test("**Round limit rejected:** `1` — a discussion needs 2 to 10 rounds."), "discuss-rounds-out-of-range/refusal-line: the fixed line passes, plain or marked up");
  expect(!rej1.test("Round limit rejected: 12 — a discussion needs 2 to 10 rounds.") && !rej1.test("Round limit rejected: 1.") && !rej1.test("A discussion takes exactly one model: sol, astra names two.") && !rej1.test("I cannot start that."), "refusal-line (rounds): another value, no range or another refusal fails");
  const ncs = read("discuss-rounds-out-of-range", "no-consult-script");
  expect(/^type: tool_used$/m.test(ncs) && /^tool: Bash$/m.test(ncs) && /^max: 0$/m.test(ncs), "no-consult-script allows none");
  const consult = re("discuss-rounds-out-of-range", "no-consult-script");
  expect(consult.test(cmd("python '/x/ask-codex/skills/ask/scripts/consult.py' resolve '/tmp/r.json'")) && !consult.test(cmd("ls /w")) && !consult.test(cmd("cat docs/constraints.md")), "no-consult-script: a consult.py command is caught, other commands are not");
  const wr = read("discuss-rounds-out-of-range", "no-file-written");
  expect(/^type: tool_used$/m.test(wr) && /^tool: Write$/m.test(wr) && /^max: 0$/m.test(wr), "no-file-written: no Write tool use");
  expect(re("discuss-rounds-out-of-range", "no-codex-call").source === re("discuss-two-models-refused", "no-codex-call").source, "discuss-rounds-out-of-range/no-codex-call is the two-models grader");
  const tools = (c) => prompt(c).match(/^allowed_tools: .*$/m)[0];
  expect(!/AskUserQuestion/.test(tools("discuss-headless-default")) && !/AskUserQuestion/.test(tools("discuss-rounds-out-of-range")), "ticket 03 cases are headless: the question tool is not offered");
  expect(userMessage("discuss-headless-default").startsWith("/ask-codex:discuss design rate limiting") && !/\brounds\b/.test(userMessage("discuss-headless-default")), "discuss-headless-default: the command carries no round count");
  expect(userMessage("discuss-rounds-out-of-range").startsWith("/ask-codex:discuss rounds 1 "), "discuss-rounds-out-of-range: the command carries rounds 1");
}
// --- Ticket 04: a round that cannot complete ends the discussion with a partial report ----------------------------------------------
{
  const NEW = { "discuss-round-fails": "fail", "discuss-unstructured-ends": "unstructured" };
  const scenarioOf = (c) => JSON.parse(text(evals, c, "scaffold.sh").match(/cat > \.stub\/scenario\.json <<'EOF'\n([\s\S]*?)\nEOF\n/)[1]);
  const early = scenarioOf("discuss-early-consensus").exec.sequence[0];
  for (const [c, mode] of Object.entries(NEW)) {
    for (const f of ["case.yaml", "prompt.md", "scaffold.sh"]) expect(fs.existsSync(path.join(evals, c, f)), `${c}/${f} exists`);
    expect(new RegExp(`^name: ${c}$`, "m").test(text(evals, c, "case.yaml")) && /^tags: \[discuss-skill\]$/m.test(text(evals, c, "case.yaml")), `${c}: case.yaml names the case and tags it discuss-skill`);
    expect(/^description: ".+"$/m.test(prompt(c)) && /^max_turns: \d+$/m.test(prompt(c)) && /^timeout_seconds: \d+$/m.test(prompt(c)) && /^allowed_tools: \[.*\]$/m.test(prompt(c)) && !/^runs:/m.test(prompt(c)), `${c}: prompt.md has its header fields and no runs override`);
    expect(/^set -euo pipefail$/m.test(text(evals, c, "scaffold.sh")), `${c}: the scaffold stops on error`);
    expect(userMessage(c).startsWith("/ask-codex:discuss rounds 3 ") && !/AskUserQuestion/.test(prompt(c).match(/^allowed_tools: .*$/m)[0]), `${c}: the command carries rounds 3 (room for a retry or a round 3) and the session is headless`);
    // The scenario: round 1 is the early-consensus reply (the disputed Redis point), round 2 is only a mode.
    const seq = scenarioOf(c).exec.sequence;
    expect(seq.length === 2, `${c}: the sequence has the two rounds the case needs`);
    expect(JSON.stringify(seq[0]) === JSON.stringify(early), `${c}: round 1 is the early-consensus reply`);
    expect(JSON.stringify(seq[1]) === JSON.stringify({ mode }), `${c}: round 2 is exactly {"mode": "${mode}"}`);
    const errs = checkErr(seq[0].reply);
    expect(errs.length === 0, `${c}: round 1 reply fits discussion.schema.json ${errs.slice(0, 3)}`);
    const s = text(evals, c, "scaffold.sh");
    expect(/No Redis/.test(s) && /Redis/.test(seq[0].reply.points[2].statement), `${c}: C3 (a shared Redis) contradicts the constraints file`);
    for (const g of fs.readdirSync(path.join(evals, c, "graders"))) {
      const n = g.replace(/\.md$/, ""), t = read(c, n);
      if (/^pattern:|^input_match:/m.test(t)) expect((() => { try { re(c, n); return true; } catch { return false; } })(), `${c}/${n}: the pattern compiles as a JavaScript regex`);
      expect(!/\(\?i\)/.test(t) && !/exec-calls/.test(t) && (!/^type: tool_used$/m.test(t) || /^tool: Bash$/m.test(t)), `${c}/${n}: no inline flags, no exec-calls, no Skill-tool grader`);
      const p = t.match(/^  path: (.+)$/m);
      if (p) expect(RECORDS.has(p[1].trim()), `${c}/${n}: reads a record the stub writes`);
    }
    // The graders both cases share with discuss-limit-reached are the same files.
    for (const n of ["no-bare-cd", "no-violations", "report-sections", "two-calls", "round-2-marker"]) expect(read(c, n) === read("discuss-limit-reached", n), `${c}/${n} is the discuss-limit-reached grader`);
    expect(/^type: tool_used$/m.test(read(c, "no-bare-cd")) && /^max: 0$/m.test(read(c, "no-bare-cd")), `${c}/no-bare-cd allows none`);
    expect(["round-2-incomplete", "c3-unresolved-ended", "no-round-2-stance"].every((n) => fs.existsSync(path.join(evals, c, "graders", `${n}.md`))), `${c}: has the three partial-report graders`);
    for (const n of ["round-2-incomplete", "c3-unresolved-ended", "no-round-2-stance"]) expect(read(c, n) === read("discuss-round-fails", n), `${c}/${n} is the same file in both cases`);
    expect(/^type: regex$/m.test(read(c, "c3-unresolved-ended")) && !/^target:/m.test(read(c, "c3-unresolved-ended")) && /^match: not_contains$/m.test(read(c, "no-round-2-stance")) && !/^target:/m.test(read(c, "no-round-2-stance")), `${c}: the partial-report graders grade the final response`);
  }
  // The stub's round 2: a failing exit, and plain text that is not the discussion schema.
  const stubText = text(evals, "_harness", "stub", "codex-stub.py");
  expect(/if mode == "fail":\n\s+sys\.stderr\.write\([^\n]*\n\s+sys\.exit\(1\)/.test(stubText) && /elif mode == "unstructured":\n\s+reply = "I looked at the code and I think the timeout handling is the problem\."/.test(stubText), "stub: `fail` exits 1 without a reply, `unstructured` answers the timeout sentence");
  expect(/call n \(1-based/.test(stubText), "stub: exec.sequence gives call n the settings of entry n");

  // --- the graders on crafted partial reports -------------------------------------------------------------------------------------
  const PART = (round2, tail = "") => [
    "## Discussion process", "Topic: rate limiting for login()", "Model: gpt-6-sol (high)", "Round limit: 3", "MCP policy: all MCP servers disabled",
    "Round 1: C1 and C2 matched my L2 and L3; C3 (shared Redis) disputed by me against docs/constraints.md:3.",
    round2, tail,
    "", "## Agreed", "- L2 = C1: Count failed attempts per username and per IP.", "- L3 = C2: Return one error text.",
    "", "## For you to decide", "- C3 — Keep the failure counters in a shared Redis instance. (unresolved because the discussion ended)",
    "  Claude recommends: in-process counters — docs/constraints.md:3 forbids Redis.",
    "  Codex recommends: a shared store — a later second instance would lose the limit.",
  ].join("\n");
  const FAILED = PART("Round 2: did not complete — the run failed (Codex exited with an error).");
  const UNSTR = PART("Round 2: did not complete — the reply was unstructured.", "Unstructured reply: \"I looked at the code and I think the timeout handling is the problem.\"");
  const inc = re("discuss-round-fails", "round-2-incomplete");
  expect(inc.test(FAILED) && inc.test(UNSTR) && inc.test(FAILED.replace("Round 2:", "**Round 2:**")) && inc.test(FAILED.replace("Round 2: ", "- Round 2: ")) && inc.test(FAILED.replace(/\n/g, "\r\n")), "round-2-incomplete: the fixed line passes, plain, marked up, in a list or with CRLF");
  expect(!inc.test(PART("Round 2: Codex maintained C3.")) && !inc.test(PART("Round 2: did not complete.")) && !inc.test(PART("Round 2: did not complete — ")) && !inc.test(PART("Round 2 did not complete — the run failed.")) && !inc.test(PART("Round 3: did not complete — the run failed.")) && !inc.test(PART("Round 2: could not finish — the run failed.")), "round-2-incomplete: a stance line, no reason, no colon, another round or other words fail");
  const unres = re("discuss-round-fails", "c3-unresolved-ended");
  expect(unres.test(FAILED) && unres.test(FAILED.replace("(unresolved because the discussion ended)", "— **unresolved because the discussion ended**")) && unres.test(FAILED.replace(/^## (.*)$/gm, "**$1**")), "c3-unresolved-ended: C3 marked with the fixed words passes, plain or marked up");
  expect(!unres.test(FAILED.replace(" (unresolved because the discussion ended)", "")) && !unres.test(FAILED.replace("unresolved because the discussion ended", "unresolved after the round limit")) && !unres.test(FAILED.replace("unresolved because the discussion ended", "split after debate")), "c3-unresolved-ended: no mark, or other words, fail");
  expect(!unres.test(FAILED.replace("- C3 — Keep", "- C4 — Keep")), "c3-unresolved-ended: C3 not among the decision items fails");
  expect(unres.test(FAILED.replace("- C3 — Keep", "- C1 — Count. (unresolved because the discussion ended)\n- C3 — Keep")), "c3-unresolved-ended: another C id listed before C3 does not matter");
  expect(!unres.test(FAILED.replace(" (unresolved because the discussion ended)", "\n- C1 — Count. (unresolved because the discussion ended)")), "c3-unresolved-ended: another C id between C3 and the mark means C3 itself is not marked");
  expect(!unres.test(FAILED.replace("- L3 = C2:", "- L3 = C3:").replace("- C3 — Keep the failure counters in a shared Redis instance. (unresolved because the discussion ended)", "- L9 — Reset the counter. (unresolved because the discussion ended)")), "c3-unresolved-ended: C3 only under Agreed fails");
  const stance = re("discuss-round-fails", "no-round-2-stance");
  expect(!stance.test(FAILED) && !stance.test(UNSTR) && !stance.test(UNSTR.replace("Round 2:", "**Round 2:**")) && !stance.test(PART("Round 2: **did not complete** — the reply was unstructured, so no stance was taken.")), "no-round-2-stance: the incomplete-round line, even one that names stances, passes");
  expect(stance.test(PART("Round 2: Codex maintained C3 (a second instance later); I maintained my objection.")) && stance.test(PART("Round 2: Codex accepted C3's removal.")) && stance.test(PART("**Round 2:** I was persuaded by Codex.")) && stance.test(PART("Round 2: did not complete — the reply was unstructured.", "Round 2: Codex revised C3.")), "no-round-2-stance: a Round 2 line reporting a stance fails (also next to the incomplete-round line)");
  expect(!stance.test(PART("Round 2: did not complete — the reply was unstructured.", "Codex maintained C3 in round 1.")), "no-round-2-stance: a stance mentioned outside a Round 2 line is not this grader's business");
  const rf = re("discuss-round-fails", "round-2-reason-failure");
  expect(rf.test(FAILED) && rf.test(PART("Round 2: did not complete — the launch failed (codex: command not found).")) && !rf.test(UNSTR) && !rf.test(PART("Round 2: did not complete — the stop was unconfirmed.")), "round-2-reason-failure: a failed run passes, an unstructured reply or another reason fails");
  const ru = re("discuss-unstructured-ends", "round-2-reason-unstructured");
  expect(ru.test(UNSTR) && !ru.test(FAILED) && !ru.test(PART("Round 2: did not complete — Codex returned no reply.")), "round-2-reason-unstructured: the unstructured reason passes, others fail");
  const lab = re("discuss-unstructured-ends", "unstructured-label");
  expect(lab.test(UNSTR) && lab.test(UNSTR.replace("Unstructured reply:", "**Unstructured reply:**")) && lab.test(UNSTR.replace("Unstructured reply: \"", "Unstructured reply:\n> \"")), "unstructured-label: the label followed by the reply passes, plain, marked up or as a block quote");
  expect(!lab.test(FAILED) && !lab.test(UNSTR.replace("Unstructured reply:", "Unstructured:")) && !lab.test(UNSTR.replace("Unstructured reply: \"I looked at the code and I think the timeout handling is the problem.\"", "Unstructured reply:")) && !lab.test(UNSTR.replace("Unstructured reply:", "The reply was unstructured:")), "unstructured-label: no label, another label or an empty label fails");
  const carried = re("discuss-unstructured-ends", "unstructured-carried");
  expect(carried.test(UNSTR) && carried.test(UNSTR.replace(/Unstructured reply: .*/, "Unstructured reply: a short note blaming how timeouts are handled — timeout")) && !carried.test(FAILED) && !carried.test(PART("Round 2: did not complete — the reply was unstructured.", "Unstructured reply: Codex wrote something." + " ".repeat(700) + "timeout")), "unstructured-carried: the content under the label passes; no label, or the word far from the label, fails");
  // The reports that the SKILL forbids would fail: an invented stance moves C3 out of the open items.
  const INVENTED = FAILED.replace("Round 2: did not complete — the run failed (Codex exited with an error).", "Round 2: Codex maintained C3 and I maintained my objection.").replace(" (unresolved because the discussion ended)", "");
  expect(!inc.test(INVENTED) && !unres.test(INVENTED) && stance.test(INVENTED), "an invented round-2 stance fails the incomplete-line, unresolved-mark and no-stance graders together");
  expect(unres.source === re("discuss-unstructured-ends", "c3-unresolved-ended").source, "c3-unresolved-ended is the same grader in both cases");

  // --- the skill states the fixed lines --------------------------------------------------------------------------------------------
  const sec = skill.slice(skill.indexOf("## A round that cannot complete"), skill.indexOf("## 8. Report"));
  expect(sec.length > 500 && skill.split("## A round that cannot complete").length === 2 && !skill.includes("A round that does not return a structured reply"), "skill: one early-end section, titled `A round that cannot complete`");
  expect(skill.indexOf("## 7. Rounds 2 to n") < skill.indexOf("## A round that cannot complete") && skill.indexOf("## A round that cannot complete") < skill.indexOf("## 8. Report"), "skill: the early-end section sits between section 7 and the report");
  expect(/Never retry it, never prepare another round, and make no further Codex call/.test(sec), "skill early end: no retry, no further round prepared, no further Codex call");
  for (const [pat, what] of [[/`failed` or `launch_failed`/, "failed or launch_failed"], [/it is stopped: the user chose to stop at a `decision_required`/, "a stop chosen at decision_required"], [/headless stop path/, "the headless stop path"], [/`stop_unconfirmed`/, "stop_unconfirmed"], [/`format: unstructured`/, "format: unstructured"], [/does not match the discussion schema/, "a schema mismatch counts as unstructured"], [/`confirmation_required`/, "confirmation_required"]])
    expect(pat.test(sec), `skill early end names the ending case: ${what}`);
  expect(/Report the uncertainty and the retained location, never claim termination/.test(sec) && /never remove the run or call cleanup/.test(sec), "skill early end: an unconfirmed stop reports uncertainty and the retained location and never claims termination");
  expect(/Never read stances, points or ids out of it/.test(sec), "skill early end: an unstructured reply is never turned into stances");
  expect(/no interactive question tool and its `prepare` or `run` returns `confirmation_required`: do not execute\. Remove the request file and report the pending items and their decline outcomes/.test(sec), "skill early end: headless confirmation_required executes nothing and reports pending items with decline outcomes");
  expect(/With an interactive question tool, a `confirmation_required` result in any round does not end the discussion: ask as `ask` says, prepare again with the answers, and run that same round\./.test(sec), "skill early end: interactive confirmation_required asks and continues the same round");
  expect(sec.includes("`Round <n>: did not complete — <reason>.`"), "skill early end: the fixed incomplete-round line");
  expect(sec.includes("`Unstructured reply:`") && sec.includes("`Pending confirmation:`") && sec.includes("`Retained location: <directory>`"), "skill early end: the labels Unstructured reply:, Pending confirmation: and Retained location:");
  expect(sec.includes("`<id> — <statement> (unresolved because the discussion ended)`") && /never marked with them/.test(sec), "skill early end: open points carry the fixed words, and a point split at the limit never does");
  expect(sec.includes("exactly `Codex recommends: none returned`") && /Codex's last returned position/.test(sec) && /Nothing from the incomplete round enters the ledger/.test(sec), "skill early end: Codex recommends its last returned position, or exactly `none returned`; nothing from the incomplete round is used");
  expect(/The `Both recommend:` line replaces the two lines only when Codex returned a position and it matches yours/.test(sec), "skill early end: Both recommend only when Codex returned a matching position");
  expect(/`Agreed`|\*\*Agreed\*\*/.test(sec) && /what was settled up to the last completed round/.test(sec), "skill early end: Agreed lists what was settled up to the last completed round");
  expect(/follow `ask`'s stop rules|`ask`'s stop operation/.test(sec) && /Run `ask`'s stop operation and collect/.test(sec), "skill early end: a stop follows ask's stop operation");
  const rep = skill.slice(skill.indexOf("## 8. Report"));
  expect(/When the discussion has ended \(nothing contested, the last round the limit allows, or a round that cannot complete/.test(rep) && rep.includes('section "A round that cannot complete"'), "skill report: also written when a round cannot complete, pointing at the early-end section");
  expect(/until nothing is contested or a round cannot complete/.test(skill) && /A round that cannot complete ends the discussion: see/.test(skill), "skill: the order of work and Running a round point at the early-end section");
}
// --- Ticket 05: concessions need evidence, late flips, blocking-only points, reopen, user calls -------------------------------------
{
  const sec7 = skill.slice(skill.indexOf("## 7. Rounds 2 to n"), skill.indexOf("## A round that cannot complete"));
  const sec6 = skill.slice(skill.indexOf("## 6. Integrate"), skill.indexOf("## 7. Rounds 2 to n"));
  const sec8 = skill.slice(skill.indexOf("## 8. Report"));
  const partial = skill.slice(skill.indexOf("## A round that cannot complete"), skill.indexOf("## 8. Report"));
  const rule4 = template.slice(template.indexOf("4. **Answer format.**"));
  // The fixed words, each once where the report rules state them, and never in the prompt files Codex sees (it must not echo them).
  for (const w of ["unevidenced concession", "late flip (round", "(your preference or authority)", "User call proposed by"]) expect(skill.includes(w), `skill: the fixed words "${w}"`);
  expect(sec8.includes("`unevidenced concession (<Codex|Claude>, <id>)`") && /that round's line/.test(sec8) && /it still took effect/.test(sec8), "skill report: an unevidenced concession is labelled on its round's process line and still took effect");
  expect(sec8.includes("`late flip (round <n>)`") && sec8.includes("`<ids>: <statement> — late flip (round <n>)`") && sec8.includes("`<id> (dropped): <statement> — late flip (round <n>)`"), "skill report: the late-flip words follow an agreed or dropped point");
  expect(sec8.includes("`<ids> — <statement> (your preference or authority)`") && /never carries the words `unresolved because the discussion ended`/.test(sec8), "skill report: a both-marked user decision item has the fixed words and never the unresolved words");
  expect(/in round 3 or later/.test(sec7) && /a reopened agreement that is agreed again counts/.test(sec7), "skill section 7: a late flip is a status change in round 3 or later");
  expect(/A concession is a change of position toward the other side/.test(sec7) && /Codex's `accept`, or its `revise` that gives up part/.test(sec7) && /specific evidence \(a `file:line` reference, a document or a counter-example\)/.test(sec7), "skill section 7: the concession definition and the evidence it needs, for both sides");
  expect(/name that evidence in the round's process line/.test(sec7) && /without one, maintain your position/.test(sec7) && /It still takes effect/.test(sec7), "skill section 7: Claude names its evidence in the process line, else maintains; an unevidenced Codex concession still takes effect");
  expect(/only when it has `new_blocking: true`, a new `C` id and a `null` stance/.test(sec7) && /without all three is ignored and mentioned/.test(sec7), "skill section 7: a new point needs new_blocking, a new id and a null stance, otherwise ignored and mentioned");
  expect(/Add a new point only when it is blocking/.test(sec7) && /new `L` id/.test(sec7), "skill section 7: Claude's own new points after round 1 are blocking-only with a new L id");
  expect(/`reopen: true` reopens it only when its reason names \(by id\) a contested point of this round/.test(sec7) && /becomes a contested point again/.test(sec7) && /A `reopen` with no such named point is ignored and mentioned/.test(sec7), "skill section 7: a reopen needs a named contested point of this round, else ignored and mentioned");
  expect(/You may reopen a tentative agreement on the same terms as Codex/.test(sec7), "skill section 7: Claude reopens on the same terms");
  expect(sec7.includes("`User call proposed by <Claude|Codex>: <reason>`") && /only when exactly one side has marked the point as a user call/.test(sec7), "skill section 7: the proposal line is in a point's block only when exactly one side marked it");
  expect(/`Tentative agreements \(locked\):`/.test(sec7) && /`Contested points:`/.test(sec7) && sec7.indexOf("`Tentative agreements (locked):`") < sec7.indexOf("`Contested points:`"), "skill section 7: the locked agreements come before the contested points, under their own heading");
  expect(/Both sides marked it: it is a user decision item as above/.test(sec6) && /not sent in any later round's context/.test(sec6) && /Only one side marked it: it keeps its status/.test(sec6), "skill section 6: both marks make a user decision item, one mark keeps the status and asks the other side");
  expect(/`User call: <reason>`/.test(skill.slice(skill.indexOf("## 5. Round 1"), skill.indexOf("## 6. Integrate"))), "skill section 5: Claude marks its own round-1 points with a `User call:` line");
  expect(/User decision items are not debated, so they do not keep a discussion going/.test(sec6), "skill section 6: user decision items do not keep the discussion going");
  expect(/in section 8's form with `\(your preference or authority\)`, never with these words/.test(partial) && partial.includes("`<id> — <statement> (unresolved because the discussion ended)`"), "skill early end: both-marked items keep their own form; open points keep the unresolved words");
  // The prompt files Codex sees: the rules for Codex, and none of Claude's report words.
  for (const w of ["unevidenced concession", "late flip", "your preference or authority"]) expect(!roundN.includes(w) && !template.includes(w) && !round1.includes(w), `prompt files do not contain "${w}"`);
  expect(/specific evidence in `evidence`/.test(roundN) && /answer `maintain`/.test(roundN) && /not evidence/.test(roundN), "round-n framing: a concession cites specific evidence in `evidence`; no new argument means `maintain`");
  expect(/`accept`, or `revise` that gives up part of your position/.test(roundN), "round-n framing: what a concession is");
  expect(/Add a new point only if it is blocking/.test(roundN) && /`new_blocking` to `true`/.test(roundN) && /set its `stance` to `null`/.test(roundN) && /Any other new point is ignored/.test(roundN), "round-n framing: blocking-only new points need new_blocking true, a new id and a null stance");
  expect(/`reopen` set to `true`/.test(roundN) && /names the contested point of this round/.test(roundN) && /is ignored/.test(roundN), "round-n framing: the reopen rule");
  expect(roundN.includes("`User call proposed by Claude: <reason>`") && /`user_call`/.test(roundN) && /`user_call_reason`/.test(roundN), "round-n framing: user-call marking and the proposal line");
  expect(/`user_call` and `user_call_reason`: `true`/.test(rule4) && /`new_blocking` and `reopen`: `false` unless/.test(rule4), "discussion.md rule 4: the four flags are explained");
  expect(!/Contested points:|Tentative agreements \(locked\)|\bL\d+\b|\bC\d+\b/.test(roundN), "round-n framing: no carried-points heading and no id a prompt grader looks for");
  expect(!/Tentative agreements \(locked\)|Contested points:/.test(rule4), "discussion.md rule 4 holds no carried-points heading");

  // --- the eval case discuss-user-call ---
  const C = "discuss-user-call";
  for (const f of ["case.yaml", "prompt.md", "scaffold.sh"]) expect(fs.existsSync(path.join(evals, C, f)), `${C}/${f} exists`);
  expect(new RegExp(`^name: ${C}$`, "m").test(text(evals, C, "case.yaml")) && /^tags: \[discuss-skill\]$/m.test(text(evals, C, "case.yaml")), `${C}: case.yaml names the case and tags it discuss-skill`);
  expect(/^description: ".+"$/m.test(prompt(C)) && /^max_turns: \d+$/m.test(prompt(C)) && /^timeout_seconds: \d+$/m.test(prompt(C)) && /^allowed_tools: \[.*\]$/m.test(prompt(C)) && !/^runs:/m.test(prompt(C)), `${C}: prompt.md has its header fields and no runs override`);
  expect(userMessage(C).startsWith("/ask-codex:discuss rounds 2 ") && !/AskUserQuestion/.test(prompt(C).match(/^allowed_tools: .*$/m)[0]), `${C}: the command carries rounds 2 and the session is headless`);
  expect(/docs\/decisions\.md/.test(userMessage(C)) && /docs\/constraints\.md/.test(userMessage(C)), `${C}: the topic points at both docs`);
  const s = text(evals, C, "scaffold.sh");
  expect(/^set -euo pipefail$/m.test(s), `${C}: the scaffold stops on error`);
  expect(/product owner's decision/.test(s) && /What a locked-out user SEES \(a CAPTCHA, or a wait message/.test(s), `${C}: the scaffold's docs say the lockout screen is the product owner's decision`);
  expect(!/exec\.sentinel|exec-stdin|exec-argv/.test(s.replace(/^#.*$/gm, "")), `${C}: the scaffold leaves the stub records to the stub`);
  const files = {};
  for (const m of s.matchAll(/cat > (\S+) <<'EOF'\n([\s\S]*?)\nEOF\n/g)) files[m[1]] = m[2].split("\n");
  const seq = JSON.parse(files[".stub/scenario.json"].join("\n")).exec.sequence;
  expect(seq.length === 2, `${C}: the sequence has the two rounds the case needs`);
  for (const [i, e] of seq.entries()) {
    const errs = checkErr(e.reply);
    expect(errs.length === 0, `${C}: round ${i + 1} reply fits discussion.schema.json ${errs.slice(0, 3)}`);
    for (const p of e.reply.points) for (const ev of p.evidence) {
      const [, file, line] = ev.match(/^(.+):(\d+)$/);
      expect(!!files[file] && (files[file][Number(line) - 1] || "").trim() !== "", `${C} round ${i + 1} ${p.id}: evidence ${ev} points at a line the scaffold wrote`);
    }
  }
  const [u1, u2] = seq.map((e) => e.reply);
  expect(JSON.stringify(u1.points.map((p) => p.id)) === '["C1","C2","C3"]' && u1.points.every((p) => p.stance === null && !p.new_blocking && !p.reopen), `${C}: round 1 raises C1, C2, C3 as new points`);
  expect(u1.points[1].user_call === true && /product owner/.test(u1.points[1].user_call_reason) && u1.points.filter((p) => p.user_call).length === 1, `${C}: only C2 is marked a user call, with a reason`);
  expect(/CAPTCHA/.test(u1.points[1].statement) && files["docs/decisions.md"][2].includes("product owner"), `${C}: C2 is the CAPTCHA-or-wait-message choice and its evidence line says the product owner decides`);
  expect(u1.points[2].reason === R3 && /Redis/.test(u1.points[2].statement) && /No Redis/.test(s), `${C}: C3 is the disputed shared-Redis point (the constraints forbid Redis)`);
  expect(u2.points.find((p) => p.id === "C3")?.stance === "maintain" && u2.points.filter((p) => p.stance === "maintain").length === 1 && !u2.points.some((p) => p.id === "C2" || p.id === "C1"), `${C}: round 2 maintains only C3 and says nothing about C1 or C2`);
  expect(u2.points.every((p) => ["accept", "maintain", "revise"].includes(p.stance) && p.user_call === false), `${C}: every round-2 point has a stance and no user call`);
  for (const g of fs.readdirSync(path.join(evals, C, "graders"))) {
    const n = g.replace(/\.md$/, ""), t = read(C, n);
    if (/^pattern:|^input_match:/m.test(t)) expect((() => { try { re(C, n); return true; } catch { return false; } })(), `${C}/${n}: the pattern compiles as a JavaScript regex`);
    expect(!/\(\?i\)/.test(t) && !/exec-calls/.test(t) && (!/^type: tool_used$/m.test(t) || /^tool: Bash$/m.test(t)), `${C}/${n}: no inline flags, no exec-calls, no Skill-tool grader`);
    const p = t.match(/^  path: (.+)$/m);
    if (p) expect(RECORDS.has(p[1].trim()), `${C}/${n}: reads a record the stub writes`);
  }
  for (const n of ["no-bare-cd", "no-violations", "report-sections", "two-calls", "round-2-marker"]) expect(read(C, n) === read("discuss-limit-reached", n), `${C}/${n} is the discuss-limit-reached grader`);
  expect(["c2-user-call-item", "c2-not-contested-round-2", "lockout-not-in-round-2", "round-2-locked-separate", "c1-not-contested-round-2"].every((n) => fs.existsSync(path.join(evals, C, "graders", `${n}.md`))), `${C}: has the five ticket-05 graders`);

  // --- the graders on crafted reports and prompts ---
  const UREPORT = [
    "## Discussion process", "Topic: rate limiting and the lockout experience for login()", "Model: gpt-6-sol (high)", "Round limit: 2", "MCP policy: all MCP servers disabled",
    "Round 1: C1 matched my L2; C2 (lockout screen) was marked a user call by both of us; C3 (shared Redis) disputed by me against docs/constraints.md:3.",
    "Round 2: Codex maintained C3 (a second instance later); I maintained my objection.",
    "", "## Agreed", "- L2 = C1: Return one error text.",
    "", "## For you to decide",
    "- L1 = C2 — When an account is locked out, show a wait message instead of a CAPTCHA. (your preference or authority)",
    "  Claude recommends: a wait message — it needs no third-party service.",
    "  Codex recommends: a wait message — it gives a bot nothing to solve.",
    "- C3 — Keep the failure counters in a shared Redis instance. (unresolved because the discussion ended)",
    "  Claude recommends: in-process counters — docs/constraints.md:3 forbids Redis.",
    "  Codex recommends: a shared store — a later second instance would lose the limit.",
  ].join("\n");
  const ui = re(C, "c2-user-call-item");
  expect(ui.test(UREPORT) && ui.test(UREPORT.replace(/Claude recommends:/, "**Claude recommends:**").replace(/Codex recommends:/, "**Codex recommends**:")), "c2-user-call-item: C2 with the fixed words and both recommendation lines passes");
  expect(ui.test(UREPORT.replace("L1 = C2 —", "C2 = L1 —")) && ui.test(UREPORT.replace(/  Claude recommends: a wait[^\n]*\n  Codex recommends: a wait[^\n]*\n/, "  Both recommend: a wait message — no third-party service and nothing for a bot to solve.\n")), "c2-user-call-item: C2 written with a Claude id, or with one Both recommend line, passes");
  expect(!ui.test(UREPORT.replace(" (your preference or authority)", "")) && !ui.test(UREPORT.replace(" (your preference or authority)", " (unresolved because the discussion ended)")), "c2-user-call-item: without the fixed words (or with the unresolved words instead) fails");
  expect(!ui.test(UREPORT.replace(/\n  Codex recommends: a wait[^\n]*/, "")) && !ui.test(UREPORT.replace(/\n  Claude recommends: a wait[^\n]*/, "")), "c2-user-call-item: a missing Codex recommends or Claude recommends line fails");
  expect(!ui.test(UREPORT.replace("L1 = C2 —", "L1 = C4 —")) && !ui.test(UREPORT.replace("- L1 = C2 — When an account is locked out, show a wait message instead of a CAPTCHA. (your preference or authority)", "- C3 — Keep the counters. (your preference or authority)\n- C2 — Lockout screen.")), "c2-user-call-item: C2 not among the items, or another C id between C2 and the fixed words, fails");
  expect(/^type: regex$/m.test(read(C, "c2-user-call-item")) && !/^target:/m.test(read(C, "c2-user-call-item")), "c2-user-call-item grades the final response");
  expect(sect.test(UREPORT), "report-sections passes the user-call report");
  const U2 = (agreed, contested) => fill(roundN, 'Respond to the contested points under "Context from Claude".',
    `Topic: ${TOPIC}\nRound: 2 of at most 2\nTentative agreements (locked):\n${agreed}\nContested points:\n${contested}`);
  const AG = "- L2 = C1: Return one error text for an unknown user and a wrong password.";
  const B3 = `- C3 (raised by Codex)\n  Statement: Keep the failure counters in a shared Redis instance.\n  Reason: ${R3}\n  Evidence: src/login.js:3\n  Claude's position: disputed — docs/constraints.md:3 forbids Redis.\n  Codex's position: raised.`;
  const GOOD2 = U2(AG, B3);
  const notC2 = re(C, "c2-not-contested-round-2"), noWords = re(C, "lockout-not-in-round-2"), sep = re(C, "round-2-locked-separate"), notC1 = re(C, "c1-not-contested-round-2");
  for (const n of ["c2-not-contested-round-2", "lockout-not-in-round-2", "c1-not-contested-round-2"]) expect(/^match: not_contains$/m.test(read(C, n)) && /path: \.stub\/exec-stdin\.2\.txt/.test(read(C, n)), `${C}/${n}: a not_contains grader on exec-stdin.2.txt`);
  expect(/path: \.stub\/exec-stdin\.2\.txt/.test(read(C, "round-2-locked-separate")), "round-2-locked-separate reads exec-stdin.2.txt");
  const B2 = "- C2 (raised by Codex)\n  Statement: When an account is locked out, show a wait message instead of a CAPTCHA.\n  Reason: Simpler.\n  Evidence: docs/decisions.md:3\n  Claude's position: raised.\n  Codex's position: raised.\n  User call proposed by Codex: docs/decisions.md says the product owner decides.";
  expect(!notC2.test(GOOD2) && notC2.test(U2(AG, B2 + "\n" + B3)) && notC2.test(U2(AG, B3 + "\n" + B2.replace("C2 (raised by Codex)", "C2 (raised by Codex)"))), "c2-not-contested-round-2: a prompt without a C2 block passes; one with a C2 block fails");
  expect(notC2.test(U2(AG, B3 + "\n- L2 = C2 (raised by Claude)\n  Statement: x")), "c2-not-contested-round-2: a merged-id header naming C2 fails too");
  expect(!notC2.test(U2("- L2 = C1: Return one error text.\n- L3 = C2: show a wait message.", B3)) , "c2-not-contested-round-2: C2 listed as a locked agreement is not a contested block (the lockout-words grader catches that)");
  expect(!noWords.test(GOOD2) && noWords.test(U2(AG, B3 + "\n- L4 (raised by Claude)\n  Statement: Show a CAPTCHA, not a wait message, to a locked-out user.")) && noWords.test(U2(AG, B3 + "\n- L4 (raised by Claude)\n  Statement: Choose between a wait message and a CAPTCHA.")), "lockout-not-in-round-2: a contested statement naming both lockout-screen options fails, under any id");
  expect(!noWords.test(U2(AG, B3 + "\n- L7 (raised by Claude)\n  Statement: login() returns presentation-neutral data, not a hardcoded message or a \"show CAPTCHA\" flag.\n  Reason: product chooses between CAPTCHA and a wait message.")), "lockout-not-in-round-2: a different point that mentions CAPTCHA in passing passes (seen in a full-suite reply)");
  expect(sep.test(GOOD2) && sep.test(U2(AG + "\n- L3 = C4: x", B3)), "round-2-locked-separate: C1 under the locked heading, then the contested heading and the C3 block, passes");
  expect(!sep.test(U2("", B3 + "\n- C1 (raised by Claude)\n  Statement: x")) && !sep.test(U2(AG, "")) && !sep.test(fill(roundN, "", `Contested points:\n${B3}\nTentative agreements (locked):\n${AG}`)) && !sep.test(U2(AG, B3.replace("C3 (raised by", "C9 (raised by").replace(/\bC3\b/g, "C9"))), "round-2-locked-separate: no locked C1, C1 only as a contested block, no contested C3 block, or the locked heading after the contested one fails");
  expect(!sep.test(U2("", B3.replace(/^/, "- C1 (raised by Claude)\n  Statement: x\n") )), "round-2-locked-separate: C1 contested instead of locked fails");
  expect(!notC1.test(GOOD2) && notC1.test(U2("", "- C1 (raised by Codex)\n  Statement: x\n" + B3)) && !notC1.test(bareN) && !notC1.test(bare1), "c1-not-contested-round-2: C1 locked passes; C1 as a contested block fails");
  expect(!sep.test(bareN) && !sep.test(bare1) && !sep.test(PROMPT1), "round-2-locked-separate: the bare template, framing or a round-1 prompt does not satisfy it");
  // A block for a one-sided user call keeps the status and carries the proposal line.
  expect(sep.test(U2(AG, B3 + "\n  User call proposed by Claude: the owner decides.")), "round-2-locked-separate: a proposal line inside C3's block does not break it");
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
