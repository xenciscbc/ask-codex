---
type: regex
pattern: 'target_root\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*\{(?=[^}]*\\?"path\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*\\?"\/var\/tmp\/ui-exercise-targets/?\\?")(?=[^}]*\\?"confirmed_by_user\\?"(?:\s|\\[nrt])*:(?:\s|\\[nrt])*true)'
target: trace
---

The request carries the target root the user gave in the conversation, marked confirmed by the user.
