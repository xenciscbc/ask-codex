---
type: regex
pattern: '(?=[\s\S]*\\?"mode\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*\\?"attach\\?"(?:\s|\\[nrt])*[,}])(?=[\s\S]*(?:\\?"chosen_by_user\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*true(?:\s|\\[nrt])*,(?:\s|\\[nrt])*\\?"owners\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*\[[^\]]*5101|\\?"owners\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*\[[^\]]*5101[^\]]*\](?:\s|\\[nrt])*,(?:\s|\\[nrt])*\\?"chosen_by_user\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*true))'
target: trace
---

The request carries attach mode and, in its attach object, the user's choice beside the confirmed owners (the skill body's own template text is no match: there `"mode": "attach"` is followed by a backtick, and `"owners"` by a placeholder).
