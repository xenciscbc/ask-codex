# The reply comes from the event stream

From release 1.5, a consultation's `codex exec` no longer gets `-o <file>`. `consult.py collect` takes Codex's reply from the run's `--json` event stream (`events.jsonl`, Codex's stdout) and, for a failed run, takes the failure reason Codex wrote there. Nothing else in the command line changed: `-s read-only --ephemeral --skip-git-repo-check --json`, `-C`, `-m`, the effort, the MCP overrides, the ADR 0008 and ADR 0010 constants, `--output-schema` and `-` with the prompt on stdin. No flag was added. The rules live in one helper, `read_stream`. A completed run's reply still reaches Claude only through `replies.classify`. There is no automatic retry and no replay.

## Why

On 2026-11-19, under codex-cli 0.170.0, every consultation failed with only `Codex execution failed` (exit 1) when the run directory was on the R: RAM disk. The session scratchpad is on that disk on the developer's machine, so every model and every project was affected. With `consult.py`'s preflight and the 1.4.0 command line, an `-o` target on R: made Codex exit 1 with `Error: Failed to open last message file "...": path contains a reparse point`. The same command line with the target on D: exited 0 with a normal turn. R:, `R:\Temp` and `R:\Temp\claude` show no reparse attribute and no link target, and 0.159.3 accepted the same path. Why Codex calls the path a reparse point was not diagnosed.

The event stream already holds the reply:

- **Equality, older CLI:** each of the five `probe-*-last.json` files in `.scratch/subagent-boundary/evidence/` equals, byte for byte, the `text` of the last `item.completed` item of type `agent_message` in its `probe-*-events.jsonl`. Each of those streams ends with `turn.completed`.
- **Probe A (0.170.0):** the 1.4.0 command line without `-o`, run directory and event file on R:. Exit 0. The events were `thread.started`, `turn.started`, `item.completed:agent_message`, `turn.completed`, and `replies.classify` returned `structured`.
- **Probe B (0.170.0):** the same command line with an unlisted model. Exit 1 and empty stderr. The events were `thread.started`, `item.completed:error`, `turn.started`, `error`, `turn.failed`, with `turn.failed.error.message` naming the unsupported model. Before 1.5, `collect` took a reason only from `stderr.log`, and only for "not logged in", so such a cause (`model_not_found` in the cc-feather failure) never reached Claude.

## The reply (D1)

`read_stream` reads `events.jsonl` line by line in binary mode. It splits on `\n` only, decodes each line as strict UTF-8, and parses it with `json.loads`. It holds one line at a time, plus the current candidate and the terminal state. There is no total size cap.

- **Events:** only a JSON object whose `type` is a string is an event.
- **Plain text:** leading whitespace and U+FEFF are stripped first, and the stripped text is what is tested and parsed. A line whose stripped text does not start with `{` is skipped, because Codex prints some errors as plain text on stdout.
- **Fail-closed lines.** Each of these means the run has no reply:
  - a line that starts with `{` but is not a JSON object;
  - a line that is not valid UTF-8;
  - a line nested too deeply to parse (`RecursionError`).

  The scan still reads the rest of the stream for the failure text.
- **Conditions for a reply.** A run has a reply only when all of these hold:
  - its exit code is 0;
  - the stream holds exactly one `turn.completed`, and it is the last event;
  - the final turn holds an `item.completed` event whose `item` is an object with `type` `agent_message` and a string `text`. The final turn is the events after the last `turn.started`, or the whole stream when there is no `turn.started`.
- **The reply** is the `text` of the last such item in the final turn. When that text is empty or only whitespace, the run has no reply. There is never a fallback to an earlier message. `item.started` and `item.updated` events, and items of other types, are never candidates.
- **Stopped, missing and unreadable.** A stopped run never has a reply, because `collect` checks the stop status first. A missing `events.jsonl` counts as an empty stream. Any other `OSError` while reading it leaves the run with no reply, whatever its exit code, and the reason becomes `Codex events could not be read`. A `MemoryError` while reading, decoding or parsing the stream, as one gigantic line can cause, is treated the same way. There is still no size cap.
- **Isolation.** Nothing in the stream's content raises out of `read_stream`: content that does not parse fails closed, and an `OSError` or a `MemoryError` marks the stream unreadable. A problem in one run's stream therefore never affects another run of the same `collect`.
- **Other readers.** `snapshot`'s bounded 64 KB tail read for `last_event` is unchanged.

Text inside another event's string fields is never the reply. For example, a `command_execution` item's `aggregated_output` may hold a line that looks like an `agent_message` event. The stream also carries command output and other repository-derived content, so only a top-level event decides.

The "exactly one `turn.completed`, last" rule answers a forgery: `events.jsonl` is Codex's stdout, and processes outside the recorded tree can inherit that handle. A notify hook chain was confirmed doing so (`.scratch/script-owned-consultation/issues/12`). Such a process could append an `agent_message` and a `turn.completed`, and a "last message, last event" rule would take the forged text. With this rule, an append yields no reply.

## The failure reason (D2)

D2 applies only when the run's exit code is not 0.

- **Source:** the text of the last `turn.failed` event with a string `error.message`. When there is none, the text of the last `error` event with a string `message`.
- **Cleaning:** every C0 control character, DEL, every C1 control character, U+2028, U+2029 and the bidi controls (U+202A to U+202E, U+2066 to U+2069) become a space. Runs of whitespace then collapse to one space, and the result is stripped.
- **Result:** the reason is `Codex reported: ` followed by the cleaned text, cut to 500 characters after cleaning. A text that is empty after cleaning, or a missing or non-string field, leaves the existing reason.
- **Precedence**, highest first:
  1. a reason the launcher wrote;
  2. the "not logged in" stderr rule;
  3. `Codex events could not be read`;
  4. the D2 text;
  5. the base reason, `Codex execution failed` or `Codex returned no usable reply`.

A run with exit 0 and no reply keeps `Codex returned no usable reply` (or the unreadable reason); D2 never applies to it. The reason is Codex-supplied text in a field that held only fixed text before. The cleaning keeps it to one line that cannot imitate a skill's fixed status lines on lines of their own. The `ask`, `review` and `discuss` skills each say that a reason starting `Codex reported:` is Codex's own text: data to report, never instructions.

## Considered options

- **Keep `-o` and move the run directory off R:.** Rejected: the run directory follows the session scratchpad or TEMP, which `consult.py` does not choose, and the failure was in how 0.170.0 opens the path, not in the plugin.
- **Take the last `agent_message` in the stream, skipping lines that do not parse.** Rejected after the security analysis: an appended message and `turn.completed` would win, and a corrupted last line or an empty last message would fall back to an earlier message.
- **Read the whole file and split it with `str.splitlines()`.** Rejected: memory grows to several times the file size, and a raw U+2028 inside a JSON string would split one event into fragments.

## Consequences and honest limits

- The reply now depends on the shape of the `--json` event stream: the event names `turn.started`, `turn.completed`, `turn.failed`, `item.completed` and `error`, and an `agent_message` item with a string `text`. If a Codex release renames or reshapes them, or stops printing the final message as an `agent_message`, consultations fail closed with `Codex returned no usable reply` rather than deliver another text. The equality with the `-o` file rests on the older CLI's five probes and one 0.170.0 probe. The 1.5.0 live acceptance checks one structured reply with the run directory on R:, and the stream tail after the notify hook has fired.
- A process holding Codex's stdout can rewrite the stream and plant a reply: it can insert an `agent_message` before Codex's own final `turn.completed`, or, because `launch()` opens `events.jsonl` with `"wb"`, seek and overwrite the file after Codex exits. Neither is detected. Only a plain append after Codex's own `turn.completed` is. The holder confirmed so far is the user's notify hook, which is the user's own configuration. Whether sandboxed commands inherit the handle is not verified. A planted text is still only an untrusted reply that Claude judges as data.
- Strict UTF-8 fails closed on a plain-text stdout line in a legacy code page, even with exit 0. Codex writes UTF-8.
- `snapshot` still raises `AttributeError` on a last line that is JSON but not an object. This predates 1.5 and is left as it is.
- Retained runs of earlier versions may still hold a `last-message.json`; pruning no longer names that file.
