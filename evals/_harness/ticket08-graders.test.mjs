// Offline check for the ticket-08 graders (copy to evals/_harness/ once slice 08 starts):
//   node evals/_harness/ticket08-graders.test.mjs
// Each deterministic grader must pass a correct sample and fail a paraphrase or a broken variant.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const evals = path.join(repo, "evals");
const grader = (c, g) => {
  const t = fs.readFileSync(path.join(evals, c, "graders", `${g}.md`), "utf8");
  return { re: new RegExp(t.match(/^pattern: '((?:[^']|'')*)'$/m)[1].replace(/''/g, "'"), "g"), match: (t.match(/^match: "?([^"\n]+)"?$/m) || [, "contains"])[1] };
};
const count = (c, g, text) => { const { re } = grader(c, g); return (text.match(re) || []).length; };
const has = (c, g, text) => count(c, g, text) > 0;
let pass = 0, fail = 0;
const check = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

// Per-run argv: five disable definitions, read-only, --disable apps.
const SERVERS = ["blender", "comfyui", "node_repl", "pencil", "cua_repl"];
const argv = (slug, servers = SERVERS) => JSON.stringify(["exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json", "-C", "/w", "-m", slug,
  "-c", 'model_reasoning_effort="medium"', ...servers.flatMap((s) => ["-c", `mcp_servers.${s}={command="ask-codex-disabled",enabled=false}`]), "--disable", "apps", "-"], null, 2);
for (const slug of ["gpt-6-astra", "gpt-5.6-sol"]) {
  check(count("parallel-two-models", `${slug}-disable-set`, argv(slug)) === 5, `${slug}: full disable set counts 5`);
  check(count("parallel-two-models", `${slug}-disable-set`, argv(slug, SERVERS.slice(1))) === 4, `${slug}: a missing disable definition counts 4 (grader count:5 fails)`);
  check(has("parallel-two-models", `${slug}-read-only`, argv(slug)), `${slug}: read-only present`);
  check(!has("parallel-two-models", `${slug}-read-only`, argv(slug).replace('"read-only"', '"workspace-write"')), `${slug}: workspace-write fails read-only`);
  check(has("parallel-two-models", `${slug}-disable-apps`, argv(slug)), `${slug}: --disable apps present`);
}

// Merged reply.
const MERGED = "Asked Codex (gpt-6-astra medium, gpt-5.6-sol high)…\n\n**Consensus**\n- [both] fetchUser … — adopt\n\n**Solo claims**\n- [gpt-6-astra] circuit breaker … — investigate\n- [gpt-5.6-sol] AbortController … — adopt\n\n**Divergences**\n- Raising the timeout: [gpt-6-astra] fixes it vs [gpt-5.6-sol] hides it — Adopted: gpt-5.6-sol — the retry loop swallows the error.";
const PARA = "Both models agree the empty object comes from swallowing timeouts. Astra also likes a circuit breaker; Sol prefers cancellation. They disagree about raising the timeout; I side with Sol.";
for (const g of ["h-consensus", "h-solo", "h-divergences", "tag-astra", "tag-sol", "adopted"]) {
  check(has("parallel-two-models", g, MERGED), `${g} matches the merged reply`);
  check(!has("parallel-two-models", g, PARA), `${g} fails the paraphrase`);
}

// Refusal, failure, parallel check.
for (const c of ["parallel-three-refused", "parallel-duplicate-refused"]) {
  check(has(c, "refusal", "Parallel consultation takes at most two different models."), `${c}: refusal line`);
  check(!has(c, "refusal", "I can only compare two models at a time."), `${c}: paraphrase fails`);
}
check(has("parallel-one-fails", "failed-line", "Failed model: gpt-5.6-sol — The Codex run failed: stub failure requested by scenario"), "failed line");
check(!has("parallel-one-fails", "failed-line", "gpt-5.6-sol failed."), "failed paraphrase fails");
// Markup seen in real replies is tolerated; a different model is not.
check(has("parallel-one-fails", "failed-line", "**Failed model:** gpt-5.6-sol — the Codex run failed"), "bold failed line passes");
check(!has("parallel-one-fails", "failed-line", "**Failed model:** gpt-6-astra — the Codex run failed"), "failed line naming the other model fails");
check(has("parallel-shared-timer", "stopped-line", "**Failed model:** `gpt-6-astra` — stopped after ~81s with no progress"), "bold + backticked stopped line passes");
check(has("parallel-shared-timer", "check-line", "Parallel check: done — `gpt-5.6-sol`; still running — `gpt-6-astra`."), "backticked slugs in the check line pass");
check(!has("parallel-two-models", "tag-astra", "- **C2** `[astra]` A circuit breaker …"), "alias tag [astra] fails the full-slug tag grader");
check(has("parallel-shared-timer", "check-line", "Parallel check: done — gpt-5.6-sol; still running — gpt-6-astra."), "check line");
check(!has("parallel-shared-timer", "check-line", "Sol finished; Astra is still running."), "check paraphrase fails");
check(!has("parallel-shared-timer", "check-line", "Parallel check: done — gpt-6-astra; still running — gpt-5.6-sol."), "swapped models fail");
check(has("parallel-shared-timer", "stopped-line", "Failed model: gpt-6-astra — stopped after 1 min without progress"), "stopped line");

// Case-5 transcript excerpt (written after the green run): nothing claim-like before the check line.
const EXCERPT = path.join(repo, ".scratch/ask-codex-mvp/evidence/parallel-shared-timer.txt");
if (fs.existsSync(EXCERPT)) {
  const text = fs.readFileSync(EXCERPT, "utf8");
  // Split at the first line that starts with the check line (the header must not satisfy this).
  const at = text.search(/^Parallel check:/m);
  check(at > 0, "the excerpt contains a line starting with 'Parallel check:'");
  // It must be written at the check itself — in an assistant text before the final reply, not only restated there.
  const lastSection = text.lastIndexOf("--- assistant text ");
  check(at > 0 && at < lastSection, "the check line appears in a message before the final reply");
  const before = at > 0 ? text.slice(0, at) : text;
  check(!/\bC[1-9]\b|Codex's summary|Consensus|Solo claims/.test(before), "no claim shown before the parallel check");
} else {
  console.log("SKIP transcript excerpt: not written yet");
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
