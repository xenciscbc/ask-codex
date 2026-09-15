### 0. Question and consultation type (before anything else)

**The question.** If the user's request contains a question, use it (without any confirmation sentences). If it does not — for example a bare `/ask-codex:ask` — infer the question from the conversation: the problem, decision, or code the user and you are currently working on. If nothing sensible can be inferred, ask the user what they want to consult Codex about (with `AskUserQuestion` when available, otherwise in plain text) and **stop here** — no temporary directory, no `codex` command, nothing to clean up. When you inferred the question, tell the user in one line what you are asking Codex (for example `Asking Codex: why does fetchUser return an empty object when the API times out?`) and continue without waiting.

A request in the user's own words ("ask Codex about this", "get Codex's opinion") is a manual consultation, exactly like `/ask-codex:ask`: do not ask for consent to consult Codex.

**The consultation type.** Pick exactly one from the conversation; it decides what Codex receives in step 7:

| Type | When | Packaging | Codex receives | Never included |
|---|---|---|---|---|
| **second opinion** | there is a Plan, decision, or implementation to be checked | with stance | the Plan / decision / implementation text (or where it lives) | secrets |
| **targeted check** | there is one specific concern about specific code or a change | with stance | the code or diff location and the concern, worded as the user or you stated it | secrets; any request for a general review |
| **diagnosis** | something does not work and the cause is unknown | blind | symptoms, evidence (errors, logs, file paths), and **every attempt that already failed, with its result** | **any root-cause hypothesis** — yours or the user's — also not as a leading question; secrets |
| **technical question** | a question of how or why, not tied to a failure | blind | the question and relevant evidence | **any stated leaning or expected answer** — yours or the user's; secrets |

Blind packaging exists so Codex's answer is independent: leave the hypothesis or leaning out of every part of the prompt (question, context, file excerpts), even when the user stated it in the same message.
