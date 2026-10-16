// Offline check for the setup skill's exercise preparation and the release documents (plan .scratch/exercise-skills C7):
//   node evals/_harness/setup-skill.test.mjs
// The setup skill names only consult.py operations that exist and run without a path, finds the ask skill as its
// sibling, and keeps the MCP policy statements; ADR 0009 is accepted with its recorded exceptions; CONTEXT.md carries
// the exercise terms; both READMEs carry the facts ticket 07 asks for.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const harness = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(harness, "..", "..");
const text = (...p) => fs.readFileSync(path.join(repo, ...p), "utf8").replace(/\r\n/g, "\n");
let pass = 0, fail = 0;
const expect = (ok, label) => { if (ok) pass++; else { fail++; console.log(`FAIL ${label}`); } };

// --- setup skill ---------------------------------------------------------------------------------------------------
const setup = text("skills", "setup", "SKILL.md");
const front = setup.match(/^---\n([\s\S]*?)\n---\n/);
expect(!!front && /^name: setup$/m.test(front[1]), "setup SKILL.md: name is setup");
expect(!!front && !/disable-model-invocation/.test(front[1]), "setup SKILL.md: model invocation unchanged (not disabled)");
expect(!!front && /\/ask-codex:ui/.test(front[1]), "setup SKILL.md: the description names /ask-codex:ui exercises");

const consult = text("skills", "ask", "scripts", "consult.py");
const choices = consult.match(/parser\.add_argument\("action", choices=\(([\s\S]*?)\)\)/);
const actions = new Set(choices ? [...choices[1].matchAll(/"([a-z-]+)"/g)].map((m) => m[1]) : []);
const noPath = consult.match(/args\.path is None and args\.action not in \(([^)]*)\)/);
const pathless = new Set(noPath ? [...noPath[1].matchAll(/"([a-z-]+)"/g)].map((m) => m[1]) : []);
const named = [...setup.matchAll(/consult\.py' ([a-z-]+)/g)].map((m) => m[1]);
expect(named.includes("browser-install") && named.includes("exercise-deps"), "setup SKILL.md: runs browser-install and exercise-deps");
for (const action of named) {
  expect(actions.has(action), `setup SKILL.md: consult.py ${action} is a consult.py action`);
  expect(pathless.has(action), `setup SKILL.md: consult.py ${action} runs without a path argument`);
}
expect(/`<ask>` is the `ask` skill directory, the sibling of this skill's base directory \(`<this skill's base directory>\/\.\.\/ask`\)/.test(setup),
  "setup SKILL.md: <ask> is the sibling ask directory");
expect(/browser-install[\s\S]*exercise-deps/.test(setup.split("## Exercise preparation")[1] || ""), "setup SKILL.md: install before the dependency check");
expect(/never remove, edit or repair it yourself/.test(setup), "setup SKILL.md: a differing install is never repaired by Claude");
expect(/It does not start the browser server or Chrome/.test(setup), "setup SKILL.md: says the check does not start the browser server");
for (const line of ["`MCP: all servers disabled for this consultation.`", "`MCP: allowed — <names>; all other servers disabled.`",
  "`MCP: minimal-deny — only node_repl and cua_repl disabled; other servers stay usable outside the sandbox.`",
  "never edit Codex's own `config.toml`", "Write the file with the Write tool only"]) {
  expect(setup.includes(line), `setup SKILL.md: keeps ${line}`);
}
const ui = text("skills", "ui", "SKILL.md");
expect(/`\/ask-codex:setup` prepares a machine/.test(ui), "ui SKILL.md: a failed dependency check points to /ask-codex:setup");

// --- ADR 0009, CONTEXT.md, manifests --------------------------------------------------------------------------------
const adr = text("docs", "adr", "0009-exercise-on-a-disposable-target.md");
expect(/^---\nstatus: accepted\n---/.test(adr), "ADR 0009: status accepted");
expect(/never write to the user's project/.test(adr) && !/never touches the user's project/.test(adr), "ADR 0009: \"never writes to\"");
for (const [label, re] of [["per-tool approval against ADR 0010", /Per-tool approval of the browser tools \(against ADR 0010/],
  ["other servers disabled against ADR 0003", /Every other MCP server disabled \(against ADR 0003/],
  ["fixed sentences against ADR 0005", /Fixed disclosure sentences \(against ADR 0005/],
  ["attach mode effects", /Attach mode: effects through the app/], ["development tools", /Both modes: the app's own development tools/]]) {
  expect(re.test(adr), `ADR 0009: records ${label}`);
}
const context = text("CONTEXT.md");
for (const term of ["**演練**（exercise）", "**可丟棄目標**（disposable target）", "**副本模式**（copy mode）", "**接上模式**（attach mode）"]) {
  expect(context.includes(term), `CONTEXT.md: defines ${term}`);
}
const plugin = JSON.parse(text(".claude-plugin", "plugin.json"));
expect(/^\d+\.\d+\.\d+$/.test(plugin.version) && plugin.skills.includes("./skills/ui") && plugin.skills.includes("./skills/setup"),
  "plugin.json: a version and the ui and setup skills");
const marketplace = JSON.parse(text(".claude-plugin", "marketplace.json"));
expect(marketplace.plugins.every((p) => p.version === undefined || p.version === plugin.version), "marketplace.json: no other version than plugin.json's");

// --- READMEs: ticket 07's facts, in both languages -------------------------------------------------------------------
const readmes = { en: text("README.md"), zh: text("README.zh-TW.md") };
const facts = {
  en: [["not an OS sandbox", /Chrome configuration plus an MCP allowlist, \*\*not an OS sandbox\*\*/],
    ["shell reaches localhost in all skills", /In every ask-codex skill — `ask`, `review`, `discuss` and the `ui` exercise — Codex's shell commands can/],
    ["not verified", /\*\*Not verified:\*\* DNS prefetch; headed mode/],
    ["difference from Codex's own browsers", /### Difference from Codex's own browsers/],
    ["version policy", /reruns probes P3–P5 and P7[\s\S]*reruns probe B1/],
    ["guard proves browser reach only", /The guard proves what the browser can reach, not what the app itself exposes or does/],
    ["-C does not hide the project", /`-C` does not hide your project from Codex's read-only shell/],
    ["tripwire", /that list is a tripwire, not a control/],
    ["attach 127.0.0.1 only", /Attach mode takes `127\.0\.0\.1` only/], ["copy [::1] fails closed", /accepts `\[::1\]` in the request, but the guard then fails closed/],
    ["own projects only", /\*\*Own projects only\.\*\*/], ["Windows only", /Windows only/]],
  zh: [["not an OS sandbox", /Chrome 設定加上 MCP allowlist，\*\*不是 OS sandbox\*\*/],
    ["shell reaches localhost in all skills", /在每個 ask-codex skill——`ask`、`review`、`discuss` 與 `ui` 演練——中，Codex 的 shell 指令都可以/],
    ["not verified", /\*\*未驗證：\*\*DNS prefetch；headed 模式/],
    ["difference from Codex's own browsers", /### 與 Codex 自有瀏覽器的差別/],
    ["version policy", /重跑 P3–P5 與 P7 探測[\s\S]*重跑 B1 探測/],
    ["guard proves browser reach only", /guard 證明的是瀏覽器能連到哪裡，不是 app 本身暴露或做了什麼/],
    ["-C does not hide the project", /`-C` 不會讓 Codex 的唯讀 shell 看不到你的專案/],
    ["tripwire", /這份清單只是警示線，不是防護/],
    ["attach 127.0.0.1 only", /接上模式只接受 `127\.0\.0\.1`/], ["copy [::1] fails closed", /請求中也接受 `\[::1\]`，但 guard 會因同樣原因 fail closed/],
    ["own projects only", /\*\*只用於你自己的專案。\*\*/], ["Windows only", /僅限 Windows/]],
};
for (const lang of ["en", "zh"]) for (const [label, re] of facts[lang]) expect(re.test(readmes[lang]), `README (${lang}): ${label}`);
for (const lang of ["en", "zh"]) {
  for (const anchor of [...readmes[lang].matchAll(/\]\(#([^)]+)\)/g)].map((m) => m[1])) {
    const slugs = [...readmes[lang].matchAll(/^#{2,3} (.+)$/gm)].map((m) => m[1].toLowerCase().replace(/[^\p{L}\p{N}\s_-]/gu, "").replace(/ /g, "-"));
    expect(slugs.includes(decodeURIComponent(anchor)), `README (${lang}): anchor #${anchor} names a heading`);
  }
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
