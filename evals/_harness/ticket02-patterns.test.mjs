// Offline check for the ticket-02 stdin graders (run before any paid eval run):
//   node evals/_harness/ticket02-patterns.test.mjs
// Reads the generated graders and scaffolds, so it tests the exact patterns the harness will use.
// 1. Samples: each pattern accepts/rejects hand-written prompt excerpts as intended.
// 2. Isolation: no stdin pattern matches any file its case's scaffold creates, so a positive
//    grader can only pass from the conversation or the skill, and a negative one cannot fail
//    just because Claude quoted the scaffold's code.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const evals = path.join(repo, "evals");
const framing = (t) => fs.readFileSync(path.join(repo, "skills/ask/prompts/framing", `${t}.md`), "utf8");

const readGrader = (file) => {
  const text = fs.readFileSync(file, "utf8");
  const pat = text.match(/^pattern: '((?:[^']|'')*)'$/m);
  if (!pat) return null;
  return {
    pattern: pat[1].replace(/''/g, "'"),
    match: (text.match(/^match: (\S+)$/m) || [, "contains"])[1],
    path: (text.match(/^\s+path: (\S+)$/m) || [, null])[1],
  };
};
const scaffoldFiles = (dir) => {
  const sh = fs.readFileSync(path.join(dir, "scaffold.sh"), "utf8");
  const out = {};
  for (const m of sh.matchAll(/cat > '([^']+)' <<'EOF'\n([\s\S]*?)EOF\n/g)) out[m[1]] = m[2];
  return out;
};

const cases = fs.readdirSync(evals).filter((d) => {
  const f = path.join(evals, d, "case.yaml");
  return fs.existsSync(f) && /tags: \[ticket-02\]/.test(fs.readFileSync(f, "utf8"));
});
const graders = {};
for (const c of cases) {
  graders[c] = {};
  for (const g of fs.readdirSync(path.join(evals, c, "graders"))) {
    const r = readGrader(path.join(evals, c, "graders", g));
    if (r && r.path === ".stub/exec-stdin.txt") graders[c][g.replace(/\.md$/, "")] = r;
  }
}

let fail = 0, pass = 0;
const re = (c, g) => {
  const r = graders[c]?.[g];
  if (!r) { fail++; console.log(`FAIL missing grader ${c}/${g}`); return null; }
  return new RegExp(r.pattern);
};
const expect = (c, g, sample, want, label) => {
  const r = re(c, g);
  if (!r) return;
  const got = r.test(sample);
  if (got === want) pass++; else { fail++; console.log(`FAIL ${c}/${g} ${want ? "should match" : "should not match"}: ${label}`); }
};

// --- samples ---
const plainUserJs = scaffoldFiles(path.join(evals, "diagnosis-blind"))["src/user.js"];
for (const c of ["diagnosis-blind", "diagnosis-leak-control"]) {
  for (const s of ["the api client drops the Authorization header on retries", "authorization header", "auth header dropped on retry", "Auth header", "the authentication header"])
    expect(c, "no-hypothesis", s, true, s);
  expect(c, "no-hypothesis", "Tried raising the timeout to 10 seconds (still fails) and adding a retry (still fails).", false, "attempts only");
  for (const s of ["raised the timeout to 10 seconds", "timeout of 10s", "a 10 sec timeout", "a 10 second timeout", "a 10-second timeout"]) expect(c, "failed-attempt-10s", s, true, s);
  expect(c, "failed-attempt-10s", "api.get(url, { timeout: 2000 })", false, "timeout: 2000");
  expect(c, "failed-attempt-retry", "and adding a retry (still fails)", true, "fixture retry sentence");
  expect(c, "failed-attempt-retry", `${plainUserJs}\nTried raising the timeout to 10 seconds (still fails).`, false, "plain fetchUser source + 10 s attempt, no retry attempt");
  expect(c, "marker-diagnosis", framing("diagnosis"), true, "diagnosis framing");
}
for (const [i, s, want] of [[1, "API_KEY=sk-test-FAKE-1234567890abcdef", true], [2, "the key …FAKE-1234…", true], [3, "ends in 1234567890abcdef", true], [1, "API_KEY=<withheld>", false], [2, "API_KEY=<withheld>", false], [3, "API_KEY=<withheld>", false]])
  expect("secret-not-sent", `no-token-${i}`, s, want, s);
expect("second-opinion-with-stance", "challenge-sent", framing("second-opinion"), true, "second-opinion framing");
expect("second-opinion-with-stance", "challenge-sent", "PLAN: wrap api.get in a circuit breaker and return a cached user when the breaker is open.", false, "plan without challenge sentence");
expect("second-opinion-with-stance", "plan-sent", "wrap api.get in a circuit breaker", true, "plan text");
expect("second-opinion-with-stance", "plan-sent", "wrap api.get in a Circuit-Breaker", true, "plan text variant");
expect("targeted-check", "concern-sent", "does fetchUser swallow errors other than TimeoutError?", true, "concern verbatim");
expect("targeted-check", "no-general-review", framing("targeted-check"), false, "targeted-check framing");
for (const s of ["Please review the whole file", "review the entire module", "Review full code"]) expect("targeted-check", "no-general-review", s, true, s);
expect("technical-question-blind", "no-leaning", "I think AbortController is always better.", true, "leaning");
expect("technical-question-blind", "no-leaning", `${framing("technical-question")}\nWhat is the difference between an AbortController-based timeout and a library timeout option?`, false, "framing + neutral question");
expect("technical-question-blind", "question-sent", "an AbortController-based timeout", true, "question");
expect("manual-without-question", "inferred-attempt", "They already tried a 10 second timeout", true, "10 second attempt");
expect("manual-without-question", "inferred-attempt", "and tried adding a retry", true, "retry attempt");

// Marker checks: own framing passes all four marker graders; adding another type's framing fails.
const TYPES = { "diagnosis-blind": "diagnosis", "second-opinion-with-stance": "second-opinion", "targeted-check": "targeted-check", "technical-question-blind": "technical-question" };
for (const [c, t] of Object.entries(TYPES)) {
  const own = framing(t);
  for (const [g, r] of Object.entries(graders[c]).filter(([g]) => /marker-/.test(g))) {
    const hit = new RegExp(r.pattern).test(own);
    const want = r.match !== "not_contains";
    if (hit === want) pass++; else { fail++; console.log(`FAIL ${c}/${g} on its own framing`); }
  }
  for (const other of Object.values(TYPES).filter((o) => o !== t)) {
    const g = `no-marker-${other}`;
    expect(c, g, `${own}\n${framing(other)}`, true, `own + ${other} framing (grader must catch the extra marker)`);
    expect(c, `marker-${t}`, framing(other), false, `${other} framing alone`);
  }
}

// --- isolation ---
for (const c of cases) {
  const files = scaffoldFiles(path.join(evals, c));
  for (const [g, r] of Object.entries(graders[c])) {
    for (const [f, content] of Object.entries(files)) {
      if (new RegExp(r.pattern).test(content)) { fail++; console.log(`FAIL isolation ${c}/${g} matches scaffold file ${f}`); }
      else pass++;
    }
  }
}

console.log(`${pass} passed, ${fail} failed (${cases.length} ticket-02 cases)`);
process.exit(fail ? 1 : 0);
