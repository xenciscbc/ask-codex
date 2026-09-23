// Reference implementation of the slice-03 model-token rule (documentation + offline check).
// readRequest(text, listedSlugs) -> { kind: "none" | "model", token?, effort?, invalid?, matches? }
export function readRequest(text, listedSlugs) {
  const words = text.trim().split(/\s+/);
  const parts = listedSlugs.map((s) => s.toLowerCase().split(/[-.]/));
  // A head is "slug-like" if it equals a listed slug or a contiguous run of a slug's -/. parts.
  const slugLike = (head) => {
    const h = head.toLowerCase();
    if (!h) return false;
    if (listedSlugs.some((s) => s.toLowerCase() === h)) return true;
    const hp = h.split(/[-.]/);
    return parts.some((p) => {
      for (let i = 0; i + hp.length <= p.length; i++) if (hp.every((x, j) => p[i + j] === x)) return true;
      return false;
    });
  };
  const headOf = (t) => (t.match(/^[A-Za-z0-9._-]*/) || [""])[0];

  let token = null;
  let rest = 1;
  if (/^(model|use)$/i.test(words[0]) && words[1]) { token = words[1]; rest = 2; }
  else if (words[0].includes(":") || slugLike(headOf(words[0]))) {
    token = words[0];
    // A following word that is also slug-like joins ("6 sol").
    if (!token.includes(":") && words[1] && /^[A-Za-z0-9._-]+$/.test(words[1]) && slugLike(words[1])) { token = `${token} ${words[1]}`; rest = 2; }
  }
  if (!token) return { kind: "none" };
  const [alias, effort] = token.split(":");
  if (!/^[A-Za-z0-9._:-]+( [A-Za-z0-9._-]+)?$/.test(token) || (effort !== undefined && !/^[a-z]+$/.test(effort)))
    return { kind: "model", token, invalid: true };
  const aliasParts = alias.toLowerCase().split(/[\s]+/);
  const matches = listedSlugs.filter((s) => aliasParts.every((a) => {
    const sp = s.toLowerCase().split(/[-.]/);
    const ap = a.split(/[-.]/);
    for (let i = 0; i + ap.length <= sp.length; i++) if (ap.every((x, j) => sp[i + j] === x)) return true;
    return s.toLowerCase() === a;
  }));
  return { kind: "model", token, effort, invalid: false, matches, rest: words.slice(rest).join(" ") };
}

// Two-model list (slice 08): "astra, sol …" or "astra:high, sol …" at the start of the request.
// Every item must read as a model token on its own, so a question like "Why, exactly, …" stays a question.
// readModels(text, listed) -> { kind: "single", reading } | { kind: "parallel", readings, rest }
//                           | { kind: "refused", reason: "too-many" | "duplicate" } | { kind: "invalid" }
export function readModels(text, listedSlugs) {
  const m = text.trim().match(/^((?:[^\s,]+\s*,\s*)+[^\s,]+)(?:\s+([\s\S]*))?$/);
  if (!m) return { kind: "single", reading: readRequest(text, listedSlugs) };
  const items = m[1].split(/\s*,\s*/);
  const readings = items.map((it) => readRequest(`${it} x`, listedSlugs));
  if (readings.some((r) => r.kind !== "model")) return { kind: "single", reading: readRequest(text, listedSlugs) };
  if (items.length > 2) return { kind: "refused", reason: "too-many" };
  if (readings.some((r) => r.invalid)) return { kind: "invalid" };
  const slugs = readings.map((r) => (r.matches.length === 1 ? r.matches[0] : null));
  if (slugs.every(Boolean) && slugs[0] === slugs[1]) return { kind: "refused", reason: "duplicate" };
  return { kind: "parallel", readings, rest: m[2] || "" };
}

// Self-check against the slice-03 token readings.
const LISTED = ["gpt-6-astra", "gpt-6-sol", "gpt-5.6-terra", "gpt-6-luna", "gpt-5.5"];
const Q = "Why does fetchUser in src/user.js return an empty object when the API times out?";
const cases = [
  [`sol ${Q}`, (r) => r.kind === "model" && r.matches.join() === "gpt-6-sol"],
  [`astra ${Q}`, (r) => r.matches?.join() === "gpt-6-astra"],
  [`sol:low ${Q}`, (r) => r.matches?.join() === "gpt-6-sol" && r.effort === "low"],
  [`6 ${Q}`, (r) => r.matches?.length === 4],
  [`model nova ${Q}`, (r) => r.kind === "model" && r.matches.length === 0],
  ["sol;touch${IFS}pwned " + Q, (r) => r.kind === "model" && r.invalid],
  [`gpt-5.5:max ${Q}`, (r) => r.matches?.join() === "gpt-5.5" && r.effort === "max"],
  [Q, (r) => r.kind === "none"],
  ["src/user.js is slow", (r) => r.kind === "none"],
  [`6 sol ${Q}`, (r) => r.matches?.join() === "gpt-6-sol"],
  [`reserve ${Q}`, (r) => r.kind === "none"],
];
const listCases = [
  [`astra, sol ${Q}`, (r) => r.kind === "parallel" && r.readings.map((x) => x.matches.join()).join("|") === "gpt-6-astra|gpt-6-sol" && r.rest.startsWith("Why")],
  [`astra:high, sol ${Q}`, (r) => r.kind === "parallel" && r.readings[0].effort === "high" && r.readings[1].effort === undefined],
  [`astra, sol, terra ${Q}`, (r) => r.kind === "refused" && r.reason === "too-many"],
  [`sol, 6-sol ${Q}`, (r) => r.kind === "refused" && r.reason === "duplicate"],
  [`astra, sol;touch ${Q}`, (r) => r.kind === "invalid"],
  [`sol ${Q}`, (r) => r.kind === "single" && r.reading.matches?.join() === "gpt-6-sol"],
  ["Why, exactly, does fetchUser fail?", (r) => r.kind === "single" && r.reading.kind === "none"],
];
if (import.meta.url.endsWith("model-token-rule.mjs") && process.argv[1]?.endsWith("model-token-rule.mjs")) {
  let fail = 0;
  for (const [text, ok] of cases) {
    const r = readRequest(text, LISTED);
    if (!ok(r)) { fail++; console.log("FAIL", JSON.stringify(text.slice(0, 40)), JSON.stringify(r)); }
  }
  for (const [text, ok] of listCases) {
    const r = readModels(text, LISTED);
    if (!ok(r)) { fail++; console.log("FAIL list", JSON.stringify(text.slice(0, 40)), JSON.stringify(r)); }
  }
  console.log(`${cases.length + listCases.length - fail} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
}
