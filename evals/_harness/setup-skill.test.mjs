// Offline check for the setup skill and the release documents:
//   node evals/_harness/setup-skill.test.mjs
// The setup skill keeps the MCP policy statements; the manifests list the kept skills (and no `./skills/ui`, removed in
// 1.5.0) with one version; both READMEs keep the localhost risk and resolve their anchors.
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
for (const line of ["`MCP: all servers disabled for this consultation.`", "`MCP: allowed — <names>; all other servers disabled.`",
  "`MCP: minimal-deny — only node_repl and cua_repl disabled; other servers stay usable outside the sandbox.`",
  "never edit Codex's own `config.toml`", "Write the file with the Write tool only"]) {
  expect(setup.includes(line), `setup SKILL.md: keeps ${line}`);
}

// --- manifests -------------------------------------------------------------------------------------------------------
const plugin = JSON.parse(text(".claude-plugin", "plugin.json"));
expect(/^\d+\.\d+\.\d+$/.test(plugin.version) && plugin.skills.includes("./skills/setup"),
  "plugin.json: a version and the setup skill");
expect(!plugin.skills.includes("./skills/ui"), "plugin.json: no ./skills/ui (removed in 1.5.0)");
const marketplace = JSON.parse(text(".claude-plugin", "marketplace.json"));
expect(marketplace.plugins.every((p) => p.version === undefined || p.version === plugin.version), "marketplace.json: no other version than plugin.json's");

// --- READMEs, in both languages --------------------------------------------------------------------------------------
const readmes = { en: text("README.md"), zh: text("README.zh-TW.md") };
const facts = {
  en: [["shell reaches localhost in all skills", /In every ask-codex skill — `ask`, `review` and `discuss` — Codex's shell commands can/]],
  zh: [["shell reaches localhost in all skills", /在每個 ask-codex skill——`ask`、`review` 與 `discuss`——中，Codex 的 shell 指令都可以/]],
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
