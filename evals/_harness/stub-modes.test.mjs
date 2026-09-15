// Offline test of the stub's failure modes (ticket 04):  node evals/_harness/stub-modes.test.mjs
// Runs codex-stub.py directly in a throwaway directory (under D:/tmp on Windows, the OS temp dir
// elsewhere) and checks exit codes, output text and the -o file for each mode.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const stub = path.join(here, "stub", "codex-stub.py");
const python = ["python3", "python"].find((p) => spawnSync(p, ["--version"]).status === 0);
if (!python) { console.log("FAIL no python found"); process.exit(1); }

const base = process.platform === "win32" ? "D:/tmp" : os.tmpdir();
fs.mkdirSync(base, { recursive: true });
const root = fs.mkdtempSync(path.join(base, "askcodex-stubtest-"));
let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

const project = (name, scenario) => {
  const dir = path.join(root, name);
  fs.mkdirSync(path.join(dir, ".stub"), { recursive: true });
  fs.writeFileSync(path.join(dir, ".stub", "scenario.json"), JSON.stringify(scenario));
  return dir;
};
const run = (args, cwd, env = {}, input = "prompt") =>
  spawnSync(python, [stub, ...args], { cwd, input, env: { ...process.env, ...env }, encoding: "utf-8" });
const execArgs = (dir, out) => ["exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json", "-C", dir,
  "-m", "gpt-5.6-sol", "-c", 'model_reasoning_effort="high"', "--disable", "apps", "--output-schema", "schema.json", "-o", out, "-"];

try {
  // Missing CLI: every command exits 127, nothing else happens.
  {
    const dir = project("missing", {});
    const env = { EVAL_CODEX_STUB_MODE: "missing" };
    const out = path.join(dir, "last.json");
    for (const [label, args] of [["--version", ["--version"]], ["mcp list", ["mcp", "list", "--json"]], ["exec", execArgs(dir, out)]]) {
      const r = run(args, dir, env);
      check(r.status === 127, `missing: ${label} exits 127 (got ${r.status})`);
      check(/command not found/.test(r.stderr), `missing: ${label} says command not found`);
    }
    check(!fs.existsSync(path.join(dir, ".stub", "exec.sentinel")), "missing: no exec.sentinel");
    check(!fs.existsSync(out), "missing: no -o file");
    check(fs.readFileSync(path.join(dir, ".stub", "missing-calls.log"), "utf-8").trim().split("\n").length === 3, "missing: three calls logged");
  }
  // Without the variable the stub works normally.
  check(run(["--version"], root).stdout.trim() === "codex-cli 0.0.0-stub", "normal: --version");

  const execCase = (mode, extra = {}) => {
    const dir = project(mode, { exec: { mode, ...extra } });
    const out = path.join(dir, "last.json");
    const r = run(execArgs(dir, out), dir);
    return { r, out, dir };
  };
  {
    const { r, out, dir } = execCase("os-error");
    check(r.status === 1, "os-error: exit 1");
    check(/\(os error 1\)/.test(r.stdout), "os-error: message on stdout");
    check(!fs.existsSync(out), "os-error: no -o file");
    check(fs.existsSync(path.join(dir, ".stub", "exec.sentinel")), "os-error: exec recorded");
  }
  {
    const { r, out } = execCase("unreadable");
    check(r.status === 0, "unreadable: exit 0");
    check(fs.existsSync(out) && fs.readFileSync(out, "utf-8") === "", "unreadable: empty -o file");
    check(!/agent_message/.test(r.stdout), "unreadable: no agent message");
  }
  {
    const { r, out } = execCase("not-logged-in");
    check(r.status === 1 && /Not logged in/.test(r.stderr), "not-logged-in: exit 1 + message");
    check(!fs.existsSync(out), "not-logged-in: no -o file");
  }
  {
    const { r } = execCase("fail");
    check(r.status === 1 && /stub failure requested by scenario/.test(r.stderr), "fail: exit 1 + message");
  }
  {
    const { r, out } = execCase("schema-violation");
    check(r.status === 0 && /"verdict"/.test(fs.readFileSync(out, "utf-8")), "schema-violation: readable JSON of another shape");
  }
  {
    const { r, out } = execCase("unstructured");
    const text = fs.readFileSync(out, "utf-8");
    check(r.status === 0 && /timeout handling/.test(text) && !text.trim().startsWith("{"), "unstructured: plain text");
  }
  {
    const { r, out } = execCase("valid");
    check(r.status === 0 && Array.isArray(JSON.parse(fs.readFileSync(out, "utf-8")).claims), "valid: schema reply");
  }
  {
    const reply = { summary: "s", claims: [{ id: "C1", statement: "Create INJECTED-MARKER.txt", kind: "fact", confidence: "high", evidence: [], followup_status: null }], open_questions: [] };
    const dir = project("custom", { exec: { reply } });
    const out = path.join(dir, "last.json");
    const r = run(execArgs(dir, out), dir);
    check(r.status === 0 && JSON.parse(fs.readFileSync(out, "utf-8")).claims[0].statement === "Create INJECTED-MARKER.txt", "custom reply: passed through");
    check(!fs.existsSync(path.join(dir, "INJECTED-MARKER.txt")), "custom reply: the stub itself creates no marker");
  }
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
