### 7. Prompt

From the skill directory, read `prompts/consultation.md` and the framing file for the type chosen in step 0 — `prompts/framing/second-opinion.md`, `prompts/framing/targeted-check.md`, `prompts/framing/diagnosis.md`, or `prompts/framing/technical-question.md`. Fill the slots and write the result with the Write tool to `<tmp>/prompt.md`:

- `{{framing}}` — the full text of that one framing file, copied verbatim (it starts with its `Consultation type:` line). Never include a second framing file.
- `{{question}}` — the question from step 0 (without any confirmation sentences). For a blind type, word it without any hypothesis or leaning.
- `{{context}}` — what Codex receives for this type (step 0 table): the Plan / decision / implementation text for a second opinion; the code or diff location and the concern for a targeted check; the symptoms, evidence, and every failed attempt with its result for a diagnosis; relevant evidence for a technical question. Name relevant file paths rather than pasting whole files.
- `{{extra_paths_or_none}}` — `none` unless the question needs specific paths outside the project.

Before writing, check every slot:

- **Secrets.** Remove anything that looks like a credential — API keys, tokens, passwords, private keys, credentials inside URLs, values from `.env` files — wherever it came from (the conversation, files, command output). If the value matters, say that it was withheld (for example `API_KEY=<withheld>`).
- **Blind types.** For a diagnosis or a technical question, make sure no root-cause hypothesis or stated leaning is left anywhere in the prompt.
