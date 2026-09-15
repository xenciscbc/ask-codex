// Unit check for the CODEX_CALL grader regex used by the eval suite.
// Run: node evals/_harness/codex-call-regex.test.mjs
// The grader's input_match sees the JSON-encoded Bash tool input, so each sample
// is encoded the same way before matching. A newline inside the command is the
// two characters `\n` after encoding, so it counts as a separator too. The
// executable may be path-prefixed (`./stubbin/codex`) or quoted (`"codex"`).
const CODEX_CALL = /"command"\s*:\s*"(?:(?:[^"\\]|\\.)*?(?:[\s(;&|]|\\n))?(?:\\"|')?(?:[^\s"'\\]*\/)?codex(?:\\"|')?\s+(?:mcp|exec)\b/;

const encode = (command, description = "Run a command") => JSON.stringify({ command, description });

const mustNotMatch = [
  encode("ls '/d/proj/.codex/config.toml'"),
  encode("cat ~/.codex/config.toml"),
  encode("mktemp -d '/r/tmp/ask-codex/XXXX'"),
  encode("echo $CODEX_HOME"),
  encode("ls", "codex exec in background"),
  encode("rm -rf -- '/r/tmp/ask-codex/run.abc'"),
  encode("echo ask-codex exec"),
];
const mustMatch = [
  encode("codex mcp list --json"),
  encode("( cd '/r/tmp/ask-codex/abc/neutral' && codex mcp list --json )"),
  encode("env -C '/r/tmp/ask-codex/abc/neutral' codex mcp list --json"),
  encode("codex exec -s read-only --ephemeral --json -C '/d/proj' - < '/r/tmp/p.md' > '/r/tmp/e.jsonl'"),
  encode('codex exec -c model_reasoning_effort="high" -s read-only -'),
  encode("TMP=/r/tmp/ask-codex/run.abc\nPROJ=/d/proj\ncodex exec -s read-only -C \"$PROJ\" -"),
  encode("./stubbin/codex exec -s read-only -"),
  encode("/home/u/.eval-stub/codex mcp list --json"),
  encode('"codex" exec -s read-only -'),
  encode("'codex' exec -s read-only -"),
];

let failed = 0;
for (const s of mustNotMatch) if (CODEX_CALL.test(s)) { failed++; console.error("UNEXPECTED MATCH:", s); }
for (const s of mustMatch) if (!CODEX_CALL.test(s)) { failed++; console.error("MISSED MATCH:", s); }
console.log(failed ? `FAIL (${failed})` : `PASS (${mustNotMatch.length} negative, ${mustMatch.length} positive)`);
process.exit(failed ? 1 : 0);
