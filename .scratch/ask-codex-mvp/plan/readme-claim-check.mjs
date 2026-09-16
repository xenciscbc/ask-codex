// Ticket 10 / F1-claims: the narrowed claim must appear verbatim in both READMEs.
//   node .scratch/ask-codex-mvp/plan/readme-claim-check.mjs [file ...]
// The expected sentence is READ FROM THE SHIPPED SKILL (skills/ask/SKILL.md), never written
// here, so editing this script cannot make a wrong README pass. The sentence must appear on one
// unbroken line with no markup inserted inside it; a wrapped or decorated copy fails.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const source = path.join(root, "skills", "ask", "SKILL.md");
const targets = process.argv.slice(2).map((f) => path.resolve(f));
if (targets.length === 0) {
  targets.push(path.join(root, "README.md"), path.join(root, "README.zh-TW.md"));
}

// The claim as the skill states it: from "Codex's shell commands run read-only" to the end of the
// MCP sentence. Anchored on both ends so a partial quote cannot satisfy it.
const CLAIM_RE = /Codex['’]s shell commands run read-only[\s\S]*?limited only by instruction\./;

const skill = fs.readFileSync(source, "utf-8");
const found = skill.match(CLAIM_RE);
if (!found) {
  console.log(`FAIL cannot read the expected sentence from ${path.relative(root, source)}`);
  process.exit(2);
}
const claim = found[0];
if (claim.includes("\n")) {
  console.log(`FAIL the sentence is not on one line in ${path.relative(root, source)}`);
  process.exit(2);
}
console.log(`expected sentence: ${claim.length} chars, read from ${path.relative(root, source)}`);

const squash = (s) => s.replace(/\s+/g, " ");
const strip = (s) => s.replace(/[*_`]/g, "");

let failed = 0;
for (const file of targets) {
  const name = path.relative(root, file) || file;
  if (!fs.existsSync(file)) {
    console.log(`FAIL ${name} does not exist`);
    failed++;
    continue;
  }
  const text = fs.readFileSync(file, "utf-8");
  const lines = text.split(/\r?\n/);
  if (lines.some((line) => line.includes(claim))) {
    console.log(`PASS ${name}`);
    continue;
  }
  failed++;
  // Say precisely how it is wrong, so a failure is actionable.
  if (squash(text).includes(squash(claim))) {
    console.log(`FAIL ${name}: the sentence is present but broken across lines — it must be one unbroken line`);
  } else if (squash(strip(text)).includes(squash(strip(claim)))) {
    console.log(`FAIL ${name}: the sentence carries markdown markup inside it — quote it unaltered`);
  } else {
    console.log(`FAIL ${name}: the sentence is missing or altered`);
  }
}

console.log(`${targets.length - failed} of ${targets.length} file(s) carry the claim verbatim`);
process.exit(failed ? 1 : 0);
