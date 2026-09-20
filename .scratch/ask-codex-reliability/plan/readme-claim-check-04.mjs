// Slice 04: the READMEs' "stopped" guarantee must match the spec and stay inside the evidence.
//   node .scratch/ask-codex-reliability/plan/readme-claim-check-04.mjs
// Same idea as .scratch/ask-codex-mvp/plan/readme-claim-check.mjs: the zh-TW promise is READ
// FROM THE SPEC (spec.md, 「已停止」的保證), never written here, so editing this script cannot make a
// wrong README pass. Every claim names the evidence file it rests on, and that file must exist.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const feature = path.resolve(here, "..");
const root = path.resolve(feature, "..", "..");
const read = (f) => fs.readFileSync(f, "utf8");
let failed = 0;
const check = (ok, label) => { console.log(`${ok ? "PASS" : "FAIL"} ${label}`); if (!ok) failed++; };

const spec = read(path.join(feature, "spec.md"));
const promise = spec.match(/停止一次諮詢時，ask-codex 會結束它啟動的整棵 Codex 行程樹[^\n]*?由使用者處理。/)?.[0];
if (!promise) { console.log("FAIL cannot read the promise sentence from spec.md"); process.exit(2); }

const EN_PROMISE = "When a consultation is stopped, ask-codex ends the whole Codex process tree it started and reports the stop only after confirming that `events.jsonl` no longer changes; if it cannot confirm that, the report says the stop is not confirmed and lists the processes still alive, for you to deal with.";
const evidence = (f) => fs.existsSync(path.join(root, f));
const LIVE = [".scratch/ask-codex-reliability/evidence/04-live-stop.md", ".scratch/ask-codex-reliability/evidence/04-live-H-watch.json", ".scratch/ask-codex-reliability/evidence/04-live-H-reply.md", ".scratch/ask-codex-reliability/evidence/04-live-I-watch.json", ".scratch/ask-codex-reliability/evidence/04-live-I-reply.md"];
const OFFLINE = ["evals/_harness/run-stop-scripts.test.mjs", "skills/ask/scripts/run.sh", "skills/ask/scripts/stop.sh"];

const files = {
  "README.md": {
    promise: EN_PROMISE,
    after: /Nothing is attributed to Codex after a stop\./,
    scripts: /two (small )?scripts/i,
    windows: /Windows[^.\n]*Git Bash[^.\n]*(both|interactive and headless)/i,
    linux: /Linux[^.\n]*(offline test)[^.\n]*(stub)/i,
    linuxOverclaim: /(tested|verified|confirmed) live on (Windows and )?Linux|Windows and Linux\b(?![^.\n]*offline)/i,
    macos: /macOS[^.\n]*untested|untested[^.\n]*macOS/i,
    residual: /one stop in (five to ten|5 to 10|5–10)/i,
    gone: /does not yet stop Codex|ends the Codex process cleanly|the process survives the stop|A fix is tracked/,
  },
  "README.zh-TW.md": {
    promise,
    after: /停止後不會有任何內容被歸給 Codex。/,
    scripts: /兩支腳本/,
    windows: /Windows[^。\n]*Git Bash[^。\n]*(兩種 session|互動[^。\n]*headless)/,
    linux: /Linux[^。\n]*離線測試[^。\n]*stub/,
    linuxOverclaim: /Windows[^。\n]{0,12}與 Linux 實測(?![^。\n]*離線)/,
    macos: /macOS[^。\n]*未(實)?測/,
    residual: /每 5 到 10 次停止/,
    gone: /不會真的停|會確實結束 Codex 行程|該行程會在停止後存活|修正已列入追蹤/,
  },
};

for (const [name, c] of Object.entries(files)) {
  const text = read(path.join(root, name));
  const lines = text.split(/\r?\n/);
  check(lines.some((l) => l.includes(c.promise)), `${name}: the promise sentence, verbatim and on one line`);
  check(c.after.test(text), `${name}: nothing is attributed to Codex after a stop`);
  check(c.scripts.test(text), `${name}: mentions the two shipped scripts`);
  check(c.windows.test(text), `${name}: Windows Git Bash, both session kinds, live`);
  check(c.linux.test(text) && !c.linuxOverclaim.test(text), `${name}: Linux by offline test and stubbed evals only — no live claim`);
  check(c.macos.test(text), `${name}: macOS untested`);
  check(c.residual.test(text), `${name}: the measured residual about where the stop line appears`);
  check(!c.gone.test(text), `${name}: the old headless-stop limitation is gone, leftovers included`);
  check(!/[\\/]scripts[\\/]|run\.sh|stop\.sh/.test(text), `${name}: no script paths or file names`);
}
for (const f of [...LIVE, ...OFFLINE]) check(evidence(f), `evidence exists: ${f}`);

console.log(failed ? `${failed} check(s) failed` : "all README claims are backed");
process.exit(failed ? 1 : 0);
