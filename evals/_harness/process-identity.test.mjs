import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..", "..");
const treeScript = path.join(repo, "skills", "ask", "scripts", "_tree.sh");
const bash = process.platform === "win32"
  ? "C:\\Program Files\\Git\\bin\\bash.exe"
  : "/bin/bash";

if (!fs.existsSync(bash)) throw new Error(`supported bash not found: ${bash}`);

const toBash = (value) => value.replace(/\\/g, "/");
const tail = "S 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 424242 20";

const withStat = (stat, callback) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "askcodex-stat-"));
  try {
    const statFile = path.join(root, "stat");
    fs.writeFileSync(statFile, stat);
    callback(statFile);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
};

const parseStarttime = (statFile) => spawnSync(bash, [
  "-c",
  String.raw`source "$1"
posix_proc_starttime "$2"`,
  "--",
  toBash(treeScript),
  toBash(statFile),
], {
  env: process.env,
  encoding: "utf8",
});

test("proc starttime parser reads a normal stat record", () => {
  withStat(`101 (worker) ${tail}\n`, (statFile) => {
    const result = parseStarttime(statFile);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, "424242\n");
  });
});

test("proc starttime parser uses the final comm delimiter with parentheses and whitespace in the name", () => {
  withStat(`102 (worker) pool\n(beta)) ${tail}\n`, (statFile) => {
    const result = parseStarttime(statFile);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, "424242\n");
  });
});

test("proc starttime parser rejects a nonnumeric starttime", () => {
  const malformedTail = tail.replace("424242", "not-a-number");
  withStat(`103 (worker) ${malformedTail}\n`, (statFile) => {
    const result = parseStarttime(statFile);
    assert.notEqual(result.status, 0);
    assert.equal(result.stdout, "");
  });
});

test("posix_identity does not use ps fallback after readable proc parsing fails", (t) => {
  const result = spawnSync(bash, [
    "-c",
    String.raw`source "$1"
[ -r "/proc/$$/stat" ] || exit 77
posix_proc_starttime() { return 1; }
ps() { printf '%s\n' 'Mon Jan  1 00:00:00 2001'; }
posix_identity "$$"`,
    "--",
    toBash(treeScript),
  ], { env: process.env, encoding: "utf8" });
  if (result.status === 77) {
    t.skip("proc stat is unavailable on this platform");
    return;
  }
  assert.notEqual(result.status, 0);
  assert.equal(result.stdout, "");
});
