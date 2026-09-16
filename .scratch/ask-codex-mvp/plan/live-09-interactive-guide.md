# Ticket 09 — interactive live scenarios (for the user)

These three scenarios need a person to answer `AskUserQuestion`, so they run in an **interactive** Claude Code session. Each uses real Codex calls (about 3–4 in total). Claude reads the session transcript afterwards and records the outcome in ticket 09.

## Setup (once)

1. Claude prepares a throwaway project at `D:\tmp\askcodex-live-09\interactive` (the fetchUser sample) — ask Claude to create it first if it is not there.
2. In a new terminal:
   ```powershell
   cd D:\tmp\askcodex-live-09\interactive
   claude --plugin-dir D:\work_data\project\skill\ask-codex
   ```
   Use one session for I1 and I2; start a fresh session for I3 (it needs an environment variable).

## I1 — Proactive consent (ticket 05 is paused; record what happens)

1. Say: `fetchUser in src/user.js returns an empty object when the API times out, and the profile page shows "user not found". Please fix it.`
2. After Claude's fix, say: `Still failing — same "user not found".` After its second fix, say again: `Still failing after the second fix. What next?`
3. Expected: a consent question with three options (Consent this once / Consent for this session / Decline) and a line saying what decision the consultation could change. Choose **Decline**. Expected: no Codex run; Claude continues alone. Say `Any other idea?` — expected: no new proposal.
4. Start a new topic the same way (e.g. `src/pages/profile.js shows "Hello undefined" for some users. Please fix it.`, two failed fixes). When asked, choose **Consent this once** — expected: one Codex run. Repeat once more with a third topic and choose **Consent for this session** — expected: one Codex run; a later fix loop in the same session consults without asking.
5. If Claude never proposes a consultation, that is the known ticket-05 issue — note it and move on.

## I2 — Override scope (moved from ticket 03)

1. In the same session: `/ask-codex:ask astra Why does renderProfile show "user not found" for existing users?`
2. Expected: an `AskUserQuestion` asking whether astra applies to this consultation only or to the rest of the session. Choose **Rest of the session**.
3. Then: `/ask-codex:ask Is the retry loop in fetchUser useful?` — expected: runs with astra, no scope question.

## I3 — Stall question (moved from ticket 07)

1. Quit the session. In PowerShell: `$env:EVAL_ASK_CODEX_TIMEOUT_MINUTES = "1"`, then start `claude --plugin-dir D:\work_data\project\skill\ask-codex` again in the same folder.
2. **Before asking anything**, tell Claude in the *main* (ask-codex) session: `I3 ready`. Claude takes a baseline of the running Codex processes and replies `go`. Wait for `go`.
3. In the interactive session, ask something slow: `/ask-codex:ask sol:xhigh Review every error path in src/ and explain which ones can hide a failed request.`
4. Expected after about a minute: either a one-line "Codex still running …" notice (it keeps waiting by itself), or a question with the options "wait another 1 minutes" / "stop this consultation" showing the elapsed time and the last event with its age. When the question appears, choose **wait** once; when it appears again, choose **stop**. Note the stop report's wording.
5. About 5 seconds after the stop, **without leaving the interactive session**, run:
   `! powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'codex%'\" | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | Format-List"`
   Its output stays in the session transcript; Claude compares it with the baseline (F8). Only then quit the session.
6. Afterwards: `Remove-Item Env:EVAL_ASK_CODEX_TIMEOUT_MINUTES`.

## When done

Tell Claude "interactive scenarios done". Claude finds the transcripts under `C:\Users\admin\.claude\projects\D--tmp-askcodex-live-09-interactive\` and records I1–I3. Then Claude deletes `D:\tmp\askcodex-live-09\`.
