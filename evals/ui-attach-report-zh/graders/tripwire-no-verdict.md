---
type: regex
pattern: '(?:Codex(?:[''’]s)?\s+shell\s+commands\s+naming|[Tt]ripwire\s*(?:\(|:)|Codex\s*的\s*shell\s*指令中提到)(?:(?!\n[ \t]*\n)[\s\S])*?(?:did\s+not\s+run|didn[''’]t\s+run|was\s+not\s+run|wasn[''’]t\s+run|were\s+not\s+run|not\s+executed|[Ee]xecuted|[Ee]xecution|was\s+blocked|were\s+blocked|been\s+blocked|[Rr]an\s+against|did\s+not\s+reach|never\s+reached|reached\s+(?:the|your)|沒有執行|未執行|已執行|有執行|被擋|擋下|已連到|沒有連到)'
match: not_contains
---

From the tripwire line to the next blank line, no verdict on whether a listed command ran, reached a server or was blocked (C8 fix E1: the script cannot know; c8a runs 9MVre9, Jfercj and 4ptNk2 added such sentences).
