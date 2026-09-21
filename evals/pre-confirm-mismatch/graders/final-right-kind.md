---
type: regex
pattern: 'I confirm this project(?:''|’)s ask-codex config `?\.claude/ask-codex\.local\.json`?, which allows the MCP server `?pencil`?'
---

The copy-back sentence in the final message is step 2's own fixed sentence, naming this project's ask-codex config and the server it really allows, `pencil` (`skills/ask/SKILL.md:41`, `:35`). Handing back the user's own sentence, which named `comfyui`, would confirm nothing (`:38`). Either apostrophe, straight or curly, is accepted, and so are inline-code backticks around the path or the name: they do not change what the sentence confirms.
