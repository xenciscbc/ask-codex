#!/usr/bin/env python3
"""Write the resumed-session history of each two-turn UI exercise case (run by run-evals.sh before the suite).

    python3 evals/_harness/gen_ui_history.py <plugin root> [<output case dir> ...]

An exercise starts only after the user answers its confirmation, and an eval run is one user turn, so a case that
needs a whole exercise resumes a session whose first turn already loaded the skill and showed the confirmation; the
case's prompt is the user's answer. That first turn is `evals/<case>/history.template.jsonl`. Claude Code records a
typed `/ask-codex:ui` as a command message followed by a meta message, `Base directory for this skill: <dir>`, a
blank line and the skill body (SKILL.md without its front matter). The template holds `{{UI_SKILL_DIR}}` and
`{{UI_SKILL_BODY}}` in place of those two; this script fills them from the plugin root it is given, so the history
always carries the current SKILL.md and the plugin's real location, and writes `evals/<case>/stubbin/history.jsonl`
(git-ignored; run-evals.sh creates and removes stubbin/). The case's `context.history_file` names that file.
"""
import json
from pathlib import Path
import sys


def skill_body(skill_md):
    text = skill_md.replace("\r\n", "\n")
    if text.startswith("---\n"):
        text = text[text.index("\n---\n", 4) + len("\n---\n"):]
    return text.lstrip("\n")


def fill(value, values):
    if isinstance(value, str):
        for placeholder, actual in values.items():
            value = value.replace(placeholder, actual)
        return value
    if isinstance(value, list):
        return [fill(item, values) for item in value]
    if isinstance(value, dict):
        return {key: fill(item, values) for key, item in value.items()}
    return value


def render(template_text, root):
    values = {"{{UI_SKILL_DIR}}": str(Path(root) / "skills" / "ui"),
              "{{UI_SKILL_BODY}}": skill_body((Path(root) / "skills" / "ui" / "SKILL.md").read_text(encoding="utf-8"))}
    lines = [json.dumps(fill(json.loads(line), values), ensure_ascii=False)
             for line in template_text.replace("\r\n", "\n").split("\n") if line.strip()]
    return "\n".join(lines) + "\n"


def main(argv):
    root = Path(argv[1]).resolve()
    cases = [Path(a) for a in argv[2:]] or sorted(p.parent for p in (root / "evals").glob("ui-*/history.template.jsonl"))
    for case in cases:
        out = case / "stubbin" / "history.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render((case / "history.template.jsonl").read_text(encoding="utf-8"), root), encoding="utf-8",
                       newline="\n")
        print(f"gen_ui_history: wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
