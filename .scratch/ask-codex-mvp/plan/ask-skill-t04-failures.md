## Failures

A consultation that cannot produce a valid opinion ends with a short, specific reason, and then you carry on. Use this table from any step:

| What you see | Tell the user |
|---|---|
| The first `codex` command fails with `command not found` / `No such file or directory`, or exit code 127 | The Codex CLI is not installed or not on PATH, so the consultation was not sent. |
| `codex exec` fails and its output mentions logging in (`Not logged in`, `codex login`, `401`, `Unauthorized`) | Codex is not logged in: run `! codex login`, then ask again. |
| The output (`stderr.log` or `events.jsonl`) contains `os error 1` | Codex cannot run in this project's location — its Windows sandbox fails on this drive (`os error 1`). |
| Any other non-zero exit | The Codex run failed: quote the most useful line of `<tmp>/stderr.log`, or, if that is empty, the last line of `<tmp>/events.jsonl`. |
| `last-message.json` is missing, empty, or not readable text | Codex returned no usable reply. |

For every failure:

- Run `codex exec` at most once per consultation (see Ground rules); never retry.
- Attribute nothing to Codex — no summary, claim, or opinion.
- Clean up (step 11).
- Then carry on with the work that led to the consultation. If the consultation was the whole request, answer the question yourself and label it clearly as your own view, not Codex's.

(Step 9 change) … If the file is readable but is not JSON matching the schema — JSON of another shape, or plain text — it is **unstructured**: do not treat it as a failure and do not turn it into claims. Present it in step 10 as an unstructured reply.

(Step 10 addition) **Unstructured reply.** Under a heading such as "Unstructured reply from Codex (did not follow the expected format)", quote Codex's text (or summarise it faithfully if long). For each point it actually makes, give your disposition — adopt, reject, or investigate — with a reason. Do not invent claim IDs, evidence, or points it did not make.
