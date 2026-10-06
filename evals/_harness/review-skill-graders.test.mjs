// Offline check for the review skill's eval cases (spec .scratch/codex-review, slice S1):
//   node evals/_harness/review-skill-graders.test.mjs
// Every new regex grader is applied to a crafted input it must pass and one it must fail, and the
// skill files are checked for the facts the graders rely on: the body marker is unique to the
// review skill, the review framing marker is unique to its framing, and the prompt template plus
// framing contain none of the words the prompt graders look for (so those graders only pass on
// what Claude filled in). The stub's canned claims are checked against the scaffold's files.
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

const CASES = ["review-working-tree", "review-base-ref", "review-range-model-focus", "review-bad-ref",
  "review-bad-range", "review-nothing-to-review", "review-nl-not-loaded", "review-not-model-invocable"];
const MARKER = "<!-- ask-codex-review-skill-body -->";
const skill = text(repo, "skills", "review", "SKILL.md");
const framing = text(repo, "skills", "review", "prompts", "framing", "review.md");
const template = text(repo, "skills", "ask", "prompts", "consultation.md");
const askSkill = text(repo, "skills", "ask", "SKILL.md");
const DISP = /[Aa]dopt|[Rr]eject|[Ii]nvestigat|ADOPT|REJECT|INVESTIGAT/;

// --- The skill files -------------------------------------------------------------------------
const front = skill.match(/^---\n([\s\S]*?)\n---\n/);
expect(!!front && /^name: review$/m.test(front[1]), "review SKILL.md: name is review");
expect(!!front && /^disable-model-invocation: true$/m.test(front[1]), "review SKILL.md: disable-model-invocation: true");
expect(!!front && /^description: .*\/ask-codex:review/m.test(front[1]), "review SKILL.md: the description names /ask-codex:review");
expect(skill.split("\n").filter((l) => l === MARKER).length === 1 && skill.split(MARKER).length === 2, "review SKILL.md: the marker is one line of its own, once");
const others = [askSkill, template, framing, text(repo, "skills", "setup", "SKILL.md"),
  ...fs.readdirSync(path.join(repo, "skills", "ask", "prompts", "framing")).map((f) => text(repo, "skills", "ask", "prompts", "framing", f))];
expect(others.every((t) => !t.includes("ask-codex-review-skill-body")), "the marker exists in no other skill or prompt file");
expect(framing.split("\n")[0] === "Consultation type: review.", "framing: the first line is the review marker");
for (const f of fs.readdirSync(path.join(repo, "skills", "ask", "prompts", "framing"))) {
  expect(!re("review-working-tree", "framing-marker").test(text(repo, "skills", "ask", "prompts", "framing", f)), `framing-marker does not match ask's ${f}`);
}
// Git hardening and ref validation (spec Solution item 1), as the skill states them.
expect(skill.includes("git --no-pager -c core.fsmonitor=false -C '<project>'"), "skill: the hardened git prefix");
expect(/every `diff` also carries `--no-ext-diff --no-textconv`/.test(skill), "skill: every diff carries --no-ext-diff --no-textconv");
expect(skill.split("\n").filter((l) => /<git> diff /.test(l)).every((l) => (l.match(/<git> diff /g) || []).length === (l.match(/<git> diff --no-ext-diff --no-textconv /g) || []).length), "skill: each written diff command carries both flags");
expect(skill.includes("rev-parse --verify --end-of-options '<ref>^{commit}'"), "skill: refs validated with rev-parse --verify --end-of-options");
expect(/A ref starting with `-` is rejected/.test(skill) && /no git command receives it/.test(skill), "skill: a ref starting with - is rejected before git sees it");
expect(/first `\.\.\.`, or else at its first `\.\.`/.test(skill) && /An empty range endpoint means `HEAD`/.test(skill), "skill: range split on ... then .., empty endpoint = HEAD");
expect(/`Scope rejected: <value exactly as typed> — <reason>\.`/.test(skill) && /`Nothing to review: <scope> has no changes\.`/.test(skill), "skill: the fixed rejection and nothing-to-review lines");
expect(/`Review scope: <kind>; <base or range>; files: <list>`/.test(skill), "skill: the fixed report scope line");
expect(!/"trigger"/.test(skill), "skill: the request file gains no trigger field");
// The ask pointer line (spec Solution item 5): exactly one line, and it names the command.
const pointer = askSkill.split("\n").filter((l) => l.includes("/ask-codex:review"));
expect(pointer.length === 1 && /not an `ask` type/.test(pointer[0]) && /cannot invoke it/.test(pointer[0]), "ask SKILL.md: one pointer line to /ask-codex:review");
const plugin = JSON.parse(text(repo, ".claude-plugin", "plugin.json"));
expect(plugin.skills.includes("./skills/review") && plugin.skills.includes("./skills/ask") && plugin.skills.includes("./skills/setup"), "plugin.json lists the review skill");

// A prompt as Claude fills it, and the bare template with the review framing and empty slots.
const fill = (q, ctx) => template.replace("{{framing}}", framing).replace("{{question}}", q).replace("{{context}}", ctx).replace("{{extra_paths_or_none}}", "none");
const bare = fill("", "");
for (const w of [/\bmain\b/, /\bHEAD\b/, /check error handling/, /src\/user\.js/, /src\/retry\.js/, /src\/cache\.js/, /src\/pages\/profile\.js/, /README\.md/]) {
  expect(!w.test(bare), `template + framing alone do not contain ${w}`);
}
const Q = 'Review the change described under "Context from Claude".';
const WT = fill(Q, "Scope: working tree; uncommitted changes against HEAD; files: M src/pages/profile.js,  M src/user.js, ?? src/cache.js\nChange intent (Claude's stance): inferred — retries and a cache for fetchUser.\nUser's focus (verbatim): none");
const BASE = fill(Q, "Scope: base; main (1f3c9e0d2b7a4c6e8f0a1b2c3d4e5f6a7b8c9d0e); files: A src/retry.js, M src/user.js\nUser's focus (verbatim): none");
const RANGE = fill(Q, "Scope: range; main..HEAD (1f3c9e0d..9a8b7c6d); files: M src/user.js\nUser's focus (verbatim): check error handling");
const TARGETED = template.replace("{{framing}}", text(repo, "skills", "ask", "prompts", "framing", "targeted-check.md")).replace("{{question}}", "Does fetchUser swallow errors?").replace("{{context}}", "src/user.js").replace("{{extra_paths_or_none}}", "none");

// --- Call counts from the stub sentinel -----------------------------------------------------------
const TS = "2026-10-01T03:04:05.123456+00:00\n";
for (const c of ["review-working-tree", "review-base-ref", "review-range-model-focus"]) {
  const one = re(c, "one-call");
  expect(/path: \.stub\/exec\.sentinel/.test(read(c, "one-call")), `${c}/one-call reads the stub sentinel`);
  expect(one.test(TS) && one.test(TS.trim()) && one.test(TS.replace("\n", "\r\n")), `${c}/one-call: one line passes`);
  expect(!one.test(TS + TS) && !one.test(""), `${c}/one-call: two lines or none fail`);
  expect(re(c, "framing-marker").test(c === "review-working-tree" ? WT : c === "review-base-ref" ? BASE : RANGE), `${c}/framing-marker: a review prompt passes`);
  expect(!re(c, "framing-marker").test(TARGETED), `${c}/framing-marker: a targeted-check prompt fails`);
  expect(/^match: not_contains$/m.test(read(c, "no-violations")) && /path: \.stub\/violations\.log/.test(read(c, "no-violations")), `${c}/no-violations is the usual stub check`);
}
const most = re("review-nl-not-loaded", "at-most-one-call");
expect(most.test("") && most.test(TS) && !most.test(TS + TS), "review-nl-not-loaded/at-most-one-call: zero or one line passes, two fail");
for (const c of ["review-bad-ref", "review-bad-range", "review-nothing-to-review", "review-not-model-invocable"]) {
  const g = read(c, "no-exec-sentinel");
  expect(/^type: file_exists$/m.test(g) && /^path: \.stub\/exec\.sentinel$/m.test(g) && /^exists: false$/m.test(g), `${c}/no-exec-sentinel: zero calls = no sentinel file`);
  expect(!/exec\.sentinel/.test(text(evals, c, "scaffold.sh")), `${c}: the scaffold does not create the sentinel`);
}
for (const c of ["review-working-tree", "review-base-ref", "review-range-model-focus"]) {
  expect(!/exec\.sentinel|exec-stdin/.test(text(evals, c, "scaffold.sh")), `${c}: the scaffold leaves the stub records to the stub`);
}
const nlScaffold = text(evals, "review-nl-not-loaded", "scaffold.sh");
expect(/^: > \.stub\/exec-stdin\.txt$/m.test(nlScaffold) && /^: > \.stub\/exec\.sentinel$/m.test(nlScaffold), "review-nl-not-loaded: the scaffold creates both records empty (a regex grader fails on a missing file)");

// --- Prompt contents ------------------------------------------------------------------------------
expect(re("review-working-tree", "file-unstaged").test(WT) && re("review-working-tree", "file-staged").test(WT) && re("review-working-tree", "file-untracked").test(WT), "review-working-tree: all three changed files pass");
expect(!re("review-working-tree", "file-untracked").test(WT.replace(", ?? src/cache.js", "")), "review-working-tree/file-untracked: a list without the untracked file fails");
expect(!re("review-working-tree", "file-staged").test(WT.replace("M src/pages/profile.js, ", "")), "review-working-tree/file-staged: a list without the staged file fails");
expect(re("review-base-ref", "base-named").test(BASE) && !re("review-base-ref", "base-named").test(BASE.replace("main ", "")), "review-base-ref/base-named: passes with main, fails with the commit id alone");
expect(re("review-base-ref", "file-added").test(BASE) && re("review-base-ref", "file-modified").test(BASE), "review-base-ref: the branch's files pass");
const nbo = re("review-base-ref", "no-base-only-file");
expect(/^match: not_contains$/m.test(read("review-base-ref", "no-base-only-file")) && !nbo.test(BASE) && nbo.test(BASE.replace("M src/user.js", "M src/user.js, M README.md")), "review-base-ref/no-base-only-file: a `git diff main` list with README.md fails");
expect(re("review-range-model-focus", "endpoint-main").test(RANGE) && re("review-range-model-focus", "endpoint-head").test(RANGE), "review-range-model-focus: both endpoints pass");
expect(!re("review-range-model-focus", "endpoint-head").test(RANGE.replace("main..HEAD ", "")), "review-range-model-focus/endpoint-head: commit ids alone fail");
expect(re("review-range-model-focus", "focus-verbatim").test(RANGE) && !re("review-range-model-focus", "focus-verbatim").test(RANGE.replace("check error handling", "check the error handling")), "review-range-model-focus/focus-verbatim: verbatim passes, a rewording fails");
const argv = (m) => JSON.stringify(["exec", "-s", "read-only", "-m", m, "-c", 'model_reasoning_effort="high"', "-c", "agents.enabled=false", "-c", "features.multi_agent_v2.enabled=false", "-"], null, 2);
const sol = re("review-range-model-focus", "model-sol");
expect(sol.test(argv("gpt-6-sol")) && !sol.test(argv("gpt-5.6-terra")) && !sol.test(argv("gpt-6-solar")), "review-range-model-focus/model-sol: only the resolved sol slug passes");
expect(/path: \.stub\/exec-argv\.json/.test(read("review-range-model-focus", "model-sol")), "review-range-model-focus/model-sol reads exec-argv.json");
for (const [c, g] of [["review-working-tree", "framing-marker"], ["review-working-tree", "file-unstaged"], ["review-base-ref", "base-named"], ["review-range-model-focus", "focus-verbatim"], ["review-range-model-focus", "endpoint-head"]]) {
  expect(/path: \.stub\/exec-stdin\.txt/.test(read(c, g)), `${c}/${g} reads exec-stdin.txt`);
}
const nfs = re("review-nl-not-loaded", "no-review-framing-sent");
expect(/^match: not_contains$/m.test(read("review-nl-not-loaded", "no-review-framing-sent")) && nfs.test(WT) && !nfs.test(TARGETED) && !nfs.test(""), "review-nl-not-loaded/no-review-framing-sent: a review prompt fails; an ask prompt or the empty file passes");

// --- The report -------------------------------------------------------------------------------------
const REPORT = [
  "Review scope: working tree; uncommitted changes against HEAD; files: src/pages/profile.js (staged), src/user.js (unstaged), src/cache.js (untracked)",
  "",
  "- **C1** (fact, high) — After the last TimeoutError, fetchUser returns an empty object instead of throwing. Evidence: `src/user.js:12`.",
  "  **Disposition: adopt.** Verified: the loop falls through to `return {}`.",
  "- **C2** (inference, medium) — The entries map in src/cache.js grows with every distinct id and never evicts anything. Evidence: `src/cache.js:4`.",
  "  **Disposition: investigate** — depends on how many users there are.",
  "- **C3** (inference, low) — renderProfile shows \"Please try again later\" for a user that really does not exist. Evidence: `src/pages/profile.js:5`.",
  "  **Disposition: reject** — a missing user returns 404, which throws.",
].join("\n");
const scope = re("review-working-tree", "scope-line");
expect(scope.test(REPORT) && scope.test("**Review scope:** working tree; …") && !scope.test("Scope: working tree") && !scope.test("Review scope: base; main"), "review-working-tree/scope-line: only the fixed working-tree line passes");
for (const n of [1, 2, 3]) {
  const d = re("review-working-tree", `disposition-c${n}`);
  expect(d.test(REPORT), `disposition-c${n}: per-claim dispositions pass`);
  expect(d.test("| ID | Claim | Disposition |\n|---|---|---|\n| C1 | timeout | Adopt — verified |\n| C2 | cache | Investigate |\n| C3 | message | Rejected |"), `disposition-c${n}: a table passes`);
  expect(d.test("Adopted: C1, C3 — verified.\nInvestigate: C2 — needs numbers."), `disposition-c${n}: a grouped form passes`);
  const missing = REPORT.split("\n").filter((l) => !(l.startsWith("  **Disposition") && REPORT.split("\n")[REPORT.split("\n").indexOf(l) - 1].includes(`**C${n}**`))).join("\n");
  expect(!d.test(missing), `disposition-c${n}: the report with C${n}'s disposition removed fails`);
}

// --- Rejected scopes ----------------------------------------------------------------------------------
const rej = re("review-bad-ref", "scope-rejected");
expect(rej.test("Scope rejected: --output=x — starts with -.") && rej.test("**Scope rejected:** `--output=x` — starts with `-`."), "review-bad-ref/scope-rejected: the fixed line passes, plain or marked up");
expect(!rej.test("I rejected the base ref --output=x because it starts with -.") && !rej.test("Scope rejected: --base — no ref given."), "review-bad-ref/scope-rejected: free wording or the wrong value fails");
const rrej = re("review-bad-range", "scope-rejected");
expect(rrej.test("Scope rejected: main..--output=x — starts with -.") && rrej.test("Scope rejected: `--output=x` — starts with -."), "review-bad-range/scope-rejected: the range or its endpoint passes");
expect(!rrej.test("Scope rejected: main — not a commit.") && !rrej.test("The range main..--output=x is invalid."), "review-bad-range/scope-rejected: another value or free wording fails");
const cmd = (s) => JSON.stringify({ command: s, description: "x" });
for (const c of ["review-bad-ref", "review-bad-range"]) {
  const opt = re(c, "no-git-gets-option-ref");
  expect(/^max: 0$/m.test(read(c, "no-git-gets-option-ref")), `${c}/no-git-gets-option-ref allows none`);
  expect(opt.test(cmd("git --no-pager -c core.fsmonitor=false -C '/w' rev-parse --verify --end-of-options '--output=x^{commit}'")), `${c}/no-git-gets-option-ref: a quoted option ref in rev-parse is caught`);
  expect(opt.test(cmd("git --no-pager -C \"/w\" diff --no-ext-diff --output=x main...HEAD")), `${c}/no-git-gets-option-ref: --output=x reaching git diff is caught`);
  expect(!opt.test(cmd("git --no-pager -c core.fsmonitor=false -C '/w' rev-parse --verify --end-of-options 'main^{commit}'")) && !opt.test(cmd("python3 --version")), `${c}/no-git-gets-option-ref: valid git commands pass`);
  const x = read(c, "no-file-x");
  expect(/^type: file_exists$/m.test(x) && /^path: x$/m.test(x) && /^exists: false$/m.test(x), `${c}/no-file-x: the file git --output=x would write must not exist`);
}
const nothing = re("review-nothing-to-review", "nothing-line");
expect(nothing.test("Nothing to review: the working tree has no changes.") && !nothing.test("There are no uncommitted changes."), "review-nothing-to-review/nothing-line: only the fixed line passes");

// --- The skill-body marker in the trace ------------------------------------------------------------------
// A body loaded through the Skill tool is recorded as a user message (seen in kept traces of the
// ask skill: `Base directory for this skill: …` followed by the body, with CRLF line ends). A
// slash-command expansion is not recorded at all (`-p --output-format stream-json`, no replay).
const traceLine = (t) => JSON.stringify({ type: "user", message: { role: "user", content: [{ type: "text", text: t }] } });
const loaded = [
  JSON.stringify({ type: "assistant", message: { content: [{ type: "tool_use", name: "Skill", input: { skill: "ask-codex:review" } }] } }),
  JSON.stringify({ type: "user", message: { content: [{ type: "tool_result", content: "Launching skill: ask-codex:review" }] } }),
  traceLine("Base directory for this skill: /mnt/d/x/ask-codex/skills/review\n\n" + skill.replace(/^---\n[\s\S]*?\n---\n/, "").replace(/\n/g, "\r\n")),
].join("\n");
const askLoaded = traceLine("Base directory for this skill: /mnt/d/x/ask-codex/skills/ask\n\n" + askSkill.replace(/^---\n[\s\S]*?\n---\n/, ""));
for (const c of ["review-nl-not-loaded", "review-not-model-invocable"]) {
  const body = re(c, "no-skill-body");
  const g = read(c, "no-skill-body");
  expect(/^target: trace$/m.test(g) && /^match: not_contains$/m.test(g), `${c}/no-skill-body is a not_contains grader on the trace`);
  expect(body.test(loaded), `${c}/no-skill-body: a Skill-tool load of the review body is found (the run fails)`);
  expect(!body.test(askLoaded), `${c}/no-skill-body: loading ask (with its pointer line) is clean`);
  expect(!body.test(traceLine("Run /ask-codex:review yourself; I cannot start it.")), `${c}/no-skill-body: naming the command is clean`);
}
const names = re("review-nl-not-loaded", "names-command");
expect(names.test("A whole-change review is `/ask-codex:review` — type it to start one.") && !names.test("I can't run that skill."), "review-nl-not-loaded/names-command: the reply must name the command");
const nmi = text(evals, "review-not-model-invocable", "scaffold.sh");
const prompt = (c) => text(evals, c, "prompt.md");
expect(/run \/ask-codex:review/.test(nmi) && !/ask-codex|review|Codex/i.test(prompt("review-not-model-invocable").split(/\n---\n/).pop()), "review-not-model-invocable: only a file the task reads asks for the review; the user's message does not");
expect(/^runs: 5$/m.test(prompt("review-nl-not-loaded")) && /^runs: 5$/m.test(prompt("review-not-model-invocable")), "both negative cases run 5 times");
expect(prompt("review-nl-not-loaded").split(/\n---\n/).pop().trim() === "use the ask-codex review skill to review my uncommitted changes", "review-nl-not-loaded: the user's own words, no slash command");

// --- Every case: slash commands, graders on the right records, stub replies that fit the files ----------------
for (const c of CASES) {
  for (const f of ["case.yaml", "prompt.md", "scaffold.sh"]) expect(fs.existsSync(path.join(evals, c, f)), `${c}/${f} exists`);
  expect(new RegExp(`^name: ${c}$`, "m").test(text(evals, c, "case.yaml")), `${c}: case.yaml names the case`);
  for (const g of fs.readdirSync(path.join(evals, c, "graders"))) {
    const t = read(c, g.replace(/\.md$/, ""));
    expect(!/exec-calls/.test(t), `${c}/${g}: never grades exec-calls/*.json`);
    expect(!/^type: (?:tool_used)$/m.test(t) || /^tool: Bash$/m.test(t), `${c}/${g}: no Skill-tool grader for a user-only skill`);
    if (/^pattern:|^input_match:/m.test(t)) expect((() => { try { re(c, g.replace(/\.md$/, "")); return true; } catch { return false; } })(), `${c}/${g}: the pattern compiles as a JavaScript regex`);
    expect(!/\(\?i\)/.test(t), `${c}/${g}: no inline flags`);
  }
  const s = text(evals, c, "scaffold.sh");
  expect(/^g init -q$/m.test(s) && /^g symbolic-ref HEAD refs\/heads\/main$/m.test(s) && /^\/\.\*$/m.test(s), `${c}: the scaffold makes its own repository on main and keeps dot files out of the scope`);
  const scen = s.match(/cat > \.stub\/scenario\.json <<'EOF'\n([\s\S]*?)\nEOF\n/);
  if (!scen) continue;
  const reply = JSON.parse(scen[1]).exec.reply;
  const files = {};
  for (const m of s.matchAll(/cat > (\S+) <<'EOF'\n([\s\S]*?)\nEOF\n/g)) files[m[1]] = m[2].split("\n");
  for (const cl of reply.claims) {
    expect(!DISP.test(cl.statement), `${c} ${cl.id}: the statement holds no disposition word`);
    for (const ev of cl.evidence) {
      const [, file, line] = ev.match(/^(.+):(\d+)$/);
      expect(!!files[file] && (files[file][Number(line) - 1] || "").trim() !== "", `${c} ${cl.id}: evidence ${ev} points at a line the scaffold wrote`);
    }
  }
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
