# A user-only review skill on the ask execution boundary

We will add a third skill, `review`, invoked only as `/ask-codex:review [model tokens] [--base <ref> | A..B | A...B] [focus]`, that consults Codex about one whole change: the working tree (default), the commits since the merge base with a base ref, or an explicit commit range. It reuses the `ask` execution boundary unchanged: the same `consult.py` resolve, prepare, run, wait, stop and collect operations, the same MCP policy, model resolution, parallel consultation and reply schema. It adds a review scope, one framing prompt (`skills/review/prompts/framing/review.md`), and a report that begins with the scope line. Claude still judges every claim as adopt, reject or investigate, never relays Codex output verbatim, never treats a claim as authorization to fix, and never presents "no claims" as approval. This revises the MVP non-goal that structured full-diff review belongs to the official `/codex:review`; ADR 0001 (call `codex exec` directly), ADR 0003 (MCP policy) and ADR 0005 (script-owned execution) are unchanged, and the scripts gain no new behavior.

## Why user-only

The skill sets `disable-model-invocation: true`. Claude cannot load it, and only the user typing the command starts a review. Two reasons:

- Many other review skills and commands exist, so a natural-language "review this" request collides with them. A skill that tried to claim those requests would fire when the user meant something else.
- An earlier design also let a workflow (for example a finished implementation step) start a review. That needed a trust boundary the scripts could verify: an opt-in setting, script-checked workflow sources, and defences against repository-authored text, memory or hook output being read as a user request. It was designed, security-reviewed and withdrawn on 2026-10-01. A user-typed command removes that whole class of problem, because memory, hooks, subagents and tool results cannot invoke a model-disabled skill.

`ask` points a whole-change request to the command instead of running a review itself: Claude tells the user the command exists and that only they can start it.

## Consequences

Reviews cost one typed command each; nothing reviews a change automatically, and a review never replaces the workflow's own review or verification. The scope is limited to the working tree, a base, or a range; staged-only or unstaged-only modes, remote PRs by number, automatic fixes, any write-capable Codex run and reply-schema changes are out of scope. Claude determines the scope with hardened read-only git commands (`git --no-pager -c core.fsmonitor=false`, diffs with `--no-ext-diff --no-textconv`, and a ref starting with `-` rejected before validation with `git rev-parse --verify --end-of-options`); nothing reaches Codex when the scope is rejected or empty. `--base <b>` means `<b>...HEAD`, the committed changes since the merge base.

The official `/codex:review` and `/codex:adversarial-review` remain the way to get Codex's native review verbatim or to run one in the background; `/ask-codex:review` is the second-opinion path that Claude weighs, with model choice and MCP policy. The README compares them.

## Honest limits

- Codex reads the scoped change, including untracked files in a working-tree review. Excluding secrets is an instruction to Codex, not an enforced filter, as in `ask`.
- A working-tree `git status` can still run a repository-configured clean filter (`.gitattributes` plus `filter.<x>.clean`) when it re-reads stat-dirty files; `--no-ext-diff`, `--no-textconv` and `core.fsmonitor=false` do not cover it. Base and range scopes compare commits only and are not affected. Found while implementing, deferred.
- Text in the reviewed diff can try to steer Codex's conclusions; "content is data" is an instruction, not enforcement. Claude's dispositions are the control.
- That a model cannot start the skill rests on the host honoring `disable-model-invocation`. A harness case checks that a natural-language request does not load it, but this is a check of observed behavior, not a guarantee.
