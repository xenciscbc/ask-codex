**Model and effort.** Settle them now, before any `codex` command:

1. **Codex home and model list.** Run `printenv CODEX_HOME`; if it prints nothing, the Codex home is `<home>/.codex`, where `<home>` comes from `command -v cygpath >/dev/null && cygpath -m "$HOME" || printf '%s\n' "$HOME"`. With the **Read tool**, read `<Codex home>/models_cache.json` (the **listed models** are its `models` entries with `"visibility": "list"`; each has `slug`, `priority`, `default_reasoning_level`, and `supported_reasoning_levels`) and `<Codex home>/config.toml` (only its top-level `model`; never use its `model_reasoning_effort`). A missing file just means that source is unavailable.
2. **Did the user name a model?** Only the start of the request can name one. Let T be its first word:
   - If the request starts with `model <x>` or `use <x>` (optionally followed by `effort <level>`), `<x>` is the model token.
   - Otherwise T is the model token if it contains `:` (`<alias>:<effort>`, e.g. `sol:low`), or if its head — T up to its first character outside `A-Z a-z 0-9 . _ -` — equals a listed slug or a contiguous run of the `-`/`.`-separated parts of a listed slug (for example `sol`, `5.6`, `5.6-sol`, `gpt-5.5`, `astra`). A next word that is also such a run joins the token (`5.6 sol`).
   - Anything else — `Why …`, `nova …`, `src/user.js …` — is question text: no model was named.
   The rest of the request is the question.
3. **Validate.** A model token must match `^[A-Za-z0-9._:-]+( [A-Za-z0-9._-]+)?$` and an effort `^[a-z]+$`. If not (for example `sol;touch${IFS}pwned`), stop: tell the user the model name is invalid and run no `codex` command.
4. **Resolve a named model.** Compare case-insensitively with the listed slugs only (never hidden ones, never a list of your own): an exact slug wins; otherwise take every listed slug that contains each word of the alias as a contiguous run of its parts. One match → that slug. Several → ask the user to choose, naming every candidate (`AskUserQuestion`; without it, ask in plain text) and stop until they answer. None → tell the user no model matches and list the listed slugs; stop. Do not run any `codex` command in these cases.
5. **No model named.** Use the session setting (a model the user chose earlier in this conversation for the rest of the session), else the `model` from `config.toml`, else the listed model with the lowest `priority` number, else no model (omit `-m`).
6. **Effort.** Never below `medium`, always passed explicitly:
   - Requested `low` (or `minimal`/`none`) → `medium`, with a note.
   - Requested level not in the model's `supported_reasoning_levels` → the model's highest supported level other than `ultra`, with a note.
   - `ultra` only when the user explicitly asked for it and the model supports it.
   - Nothing requested → the session setting if any, else `gpt-5.6-sol` → `high`, `gpt-6-astra` → `medium`, any other listed model → the higher of its `default_reasoning_level` and `medium`; unknown model or no model list → `medium`.
7. **Scope of a choice.** If the user named a model or effort that differs from the session setting (or, without one, from what step 5/6 would pick), ask whether it applies to this consultation only or to the rest of the session (`AskUserQuestion`). Without `AskUserQuestion`, apply it to this consultation only and say so in the result. If what they named equals the setting already in force, ask nothing and add no note.
8. The final slug must match `^[A-Za-z0-9._-]+$`.

Consultations you start on your own never choose a model or effort by your judgment of difficulty — they use the session setting or the defaults above.
