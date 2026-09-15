# 04 — Failure handling

**What to build:** When a consultation cannot produce a valid opinion, the user gets a short explanation and Claude carries on with its own work — no retry, and never a fabricated Codex opinion. Covered failures: Codex CLI missing; not logged in (the user is told to run `! codex login`); non-zero exit; output that violates the response schema. If the output is readable but unstructured, it is passed to Claude labelled "unstructured" and still gets dispositions. Temporary files are deleted on every failure path. See spec: user stories 68–71.

**Blocked by:** 01 — Manual consultation tracer bullet.

**Status:** ready-for-agent

- [ ] Each failure mode produces a concise user-facing reason and Claude continues the task it was doing.
- [ ] Not-logged-in failures point the user to `! codex login`.
- [ ] Exactly one Codex invocation per failed consultation (no retry).
- [ ] No claim is ever attributed to Codex unless it appears in Codex's actual output.
- [ ] Readable non-schema output is presented as unstructured with dispositions; unreadable output is reported as a failure.
- [ ] Temporary files are removed after every failure.
- [ ] Eval cases pass for: missing executable, not-logged-in error, non-zero exit, schema-violating output (both readable and unreadable), each asserting a single `codex` call and an `llm` grader that finds no fabricated claims.
