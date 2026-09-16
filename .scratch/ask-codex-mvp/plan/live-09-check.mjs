// Validate one or more Codex replies against skills/ask/consultation.schema.json (ticket 09, A1/A4/A7/A10).
//   node .scratch/ask-codex-mvp/plan/live-09-check.mjs <reply.json> [more.json ...]
// Checks the constraints the schema states: the three required top-level keys and no others,
// each claim's six required keys and no others, the two enums, and the array element types.
// Exits non-zero if any file fails, printing every problem.
import fs from "node:fs";

const TOP = ["summary", "claims", "open_questions"];
const CLAIM = ["id", "statement", "kind", "confidence", "evidence", "followup_status"];
const KIND = ["fact", "inference"];
const CONFIDENCE = ["high", "medium", "low"];
const STATUS = ["resolved", "unresolved", "invalid", "new-blocking", null];

const isStr = (v) => typeof v === "string";
const strArray = (v) => Array.isArray(v) && v.every(isStr);

function checkReply(reply, problems) {
  if (reply === null || typeof reply !== "object" || Array.isArray(reply)) {
    problems.push("the reply is not a JSON object");
    return;
  }
  for (const key of TOP) if (!(key in reply)) problems.push(`missing required key ${key}`);
  for (const key of Object.keys(reply)) if (!TOP.includes(key)) problems.push(`unexpected key ${key}`);
  if ("summary" in reply && !isStr(reply.summary)) problems.push("summary is not a string");
  if ("open_questions" in reply && !strArray(reply.open_questions)) problems.push("open_questions is not an array of strings");
  if ("claims" in reply && !Array.isArray(reply.claims)) {
    problems.push("claims is not an array");
    return;
  }
  for (const [i, claim] of (reply.claims ?? []).entries()) {
    const at = `claims[${i}]`;
    if (claim === null || typeof claim !== "object" || Array.isArray(claim)) {
      problems.push(`${at} is not an object`);
      continue;
    }
    for (const key of CLAIM) if (!(key in claim)) problems.push(`${at} missing required key ${key}`);
    for (const key of Object.keys(claim)) if (!CLAIM.includes(key)) problems.push(`${at} unexpected key ${key}`);
    if ("id" in claim && !isStr(claim.id)) problems.push(`${at}.id is not a string`);
    if ("statement" in claim && !isStr(claim.statement)) problems.push(`${at}.statement is not a string`);
    if ("kind" in claim && !KIND.includes(claim.kind)) problems.push(`${at}.kind is ${JSON.stringify(claim.kind)}, not one of ${KIND.join("/")}`);
    if ("confidence" in claim && !CONFIDENCE.includes(claim.confidence)) problems.push(`${at}.confidence is ${JSON.stringify(claim.confidence)}, not one of ${CONFIDENCE.join("/")}`);
    if ("evidence" in claim && !strArray(claim.evidence)) problems.push(`${at}.evidence is not an array of strings`);
    if ("followup_status" in claim && !STATUS.includes(claim.followup_status)) {
      problems.push(`${at}.followup_status is ${JSON.stringify(claim.followup_status)}, not one of resolved/unresolved/invalid/new-blocking/null`);
    }
  }
}

const files = process.argv.slice(2);
if (files.length === 0) {
  console.log("usage: node live-09-check.mjs <reply.json> [more.json ...]");
  process.exit(2);
}
let failed = 0;
for (const file of files) {
  const problems = [];
  let reply;
  try {
    reply = JSON.parse(fs.readFileSync(file, "utf-8"));
  } catch (err) {
    problems.push(`unreadable: ${err.message}`);
  }
  if (problems.length === 0) checkReply(reply, problems);
  if (problems.length === 0) {
    console.log(`PASS ${file} (${reply.claims.length} claims, ${reply.open_questions.length} open questions)`);
  } else {
    failed++;
    console.log(`FAIL ${file}`);
    for (const p of problems) console.log(`  - ${p}`);
  }
}
process.exit(failed ? 1 : 0);
