// Slice 04: save what the assistant wrote in a live scenario as an evidence file.
//   node .scratch/ask-codex-reliability/plan/live-04-extract-reply.mjs <transcript.jsonl> <out.md> [header line]
// Copies every assistant TEXT block in order, each under a `--- assistant text <n> ---` marker,
// and names the tool calls made between them (`[tool: Bash]`). Tool results, user and system
// text, thinking and the skill body are never copied — a transcript embeds the skill's own
// fixed wording, and only what the assistant itself wrote is evidence.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function extract(jsonl) {
  const out = [];
  let n = 0;
  for (const raw of jsonl.split(/\r?\n/)) {
    if (!raw.trim()) continue;
    let o;
    try { o = JSON.parse(raw); } catch { continue; }
    if (o.type !== "assistant" || !Array.isArray(o.message?.content)) continue;
    for (const b of o.message.content) {
      if (b.type === "text" && b.text.trim()) out.push(`--- assistant text ${++n} ---`, b.text.trimEnd());
      else if (b.type === "tool_use") out.push(`[tool: ${b.name}]`);
    }
  }
  return out.join("\n") + "\n";
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [src, dest, ...header] = process.argv.slice(2);
  if (!src || !dest) { console.error("usage: live-04-extract-reply.mjs <transcript.jsonl> <out.md> [header line]"); process.exit(2); }
  const body = extract(fs.readFileSync(src, "utf8"));
  fs.writeFileSync(dest, (header.length ? `${header.join(" ")}\n\n` : "") + body);
  console.log(`${(body.match(/^--- assistant text \d+ ---$/gm) ?? []).length} text blocks → ${dest}`);
}
