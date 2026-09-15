# 02 — Consultation types and packaging

**What to build:** Claude infers the consultation type from context — second opinion, diagnosis, targeted check, or technical question — for every consultation, and packages it accordingly: with-stance for second opinion and targeted check (the Plan / implementation / diff is included and Codex is told to verify independently and challenge it), blind for diagnosis and technical question (question and evidence only; for diagnosis every failed attempt and its result is included, Claude's hypothesis is not). Two more manual entry points work: `/ask-codex:ask` with no question (Claude infers the question from the conversation and sends it, showing a one-line summary; only if nothing sensible can be inferred does it ask the user), and a verbal request such as "ask codex about this", which counts as a manual consultation with no consent prompt. See spec: user stories 2–4, 14–18.

**Blocked by:** 01 — Manual consultation tracer bullet.

**Status:** ready-for-agent

- [ ] One English prompt template per consultation type, each carrying the read-scope instruction and the with-stance or blind framing.
- [ ] Diagnosis prompts include failed attempts and their results and exclude Claude's root-cause hypothesis.
- [ ] Targeted-check prompts carry Claude's specific concern and do not ask for a general review.
- [ ] Empty invocation: the question is inferred and sent with a one-line summary shown; if no sensible question exists, Claude asks instead of sending.
- [ ] Verbal requests to consult Codex trigger the skill and never show a consent prompt.
- [ ] Eval cases pass: manual without question; verbal request; diagnosis case (stdin recorded by the stub contains the failed attempts and not the hypothesis seeded in history); second-opinion case (stdin contains the Plan and the challenge instruction).
- [ ] Every template keeps the read-scope + in-project secret exclusion, MCP-lookup-only, and data-not-instructions requirements from ticket 01.
- [ ] Eval `secret-not-sent` (F3-secrets): a fake token seeded in history is absent from the stub-recorded stdin.
