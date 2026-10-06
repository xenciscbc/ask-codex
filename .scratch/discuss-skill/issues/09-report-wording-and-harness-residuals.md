# 09 — Small report wording drift and harness residuals from the discuss branch

Status: needs-triage

**What to build:** record and, where cheap, remove the P4 residuals the discuss branch left.

- **Report wording (verifier A4):** a self-made label `unevidenced maintain (Codex, C3)`; `Codex recommends: none returned` on a completed user call (defined only for a partial report); a count that disagrees with the list ("six points" then seven). Traces: `D:\tmp\ask-codex-r07b-traces\discuss-p6-discuss-{user-call,limit-reached}\`.
- **Bare `cd` (model habit):** about 1 run in 20–40 still runs `cd <project or scratch dir> && …` for a listing or an inline script; the skill forbids it and the same habit appears at baseline (regression set: candidate 2/27, baseline 4/27). The two discuss-specific forms (cd into `ask/scripts`, scripts that build the request JSON) stopped after b2091df.
- **Stub counter (verifier A5):** `exec-count.txt` in `evals/_harness/stub/codex-stub.py` is a plain read-modify-write; two parallel `by_model` calls could share a number. No case combines `exec.sequence` with `by_model` today.
- **Single API stalls:** two eval runs timed out after one response took about 19 minutes to start (t03 headless-default, reg-final unstructured-ends); not skill behaviour, but cases with 1500 s timeouts are sensitive to it.

**Blocked by:** None — can start immediately.

- [ ] Decide per item: fix (with an offline-proven grader where it is report wording), or accept as a documented residual.
