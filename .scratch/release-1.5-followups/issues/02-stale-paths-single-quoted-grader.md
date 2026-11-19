# 02 — `paths-single-quoted` grader still matches a hand-typed `codex exec … -o`

Status: needs-triage

Source: release-1.5, ticket 02's second plan review, item N6.

`evals/manual-with-question/graders/paths-single-quoted.md` checks a `codex exec` command line that Claude types by hand. An `-o` appears inside its `input_match` regex lookahead. Since 1.1.0, consultations are script-owned and Claude no longer types `codex exec`. Since 1.5.0, `-o` is not passed at all. Rewording the grader would change its logic, so release-1.5 left it alone.

- [ ] Decide whether the grader and its case still test anything, then rewrite or retire them.

## Comments
