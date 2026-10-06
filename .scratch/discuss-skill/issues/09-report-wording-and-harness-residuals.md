# 09 — Small report wording drift and harness residuals from the discuss branch

Status: resolved — see Comments (2026-10-06)

**What to build:** record and, where cheap, remove the P4 residuals the discuss branch left.

- **Report wording (verifier A4):** a self-made label `unevidenced maintain (Codex, C3)`; `Codex recommends: none returned` on a completed user call (defined only for a partial report); a count that disagrees with the list ("six points" then seven). Traces: `D:\tmp\ask-codex-r07b-traces\discuss-p6-discuss-{user-call,limit-reached}\`.
- **Bare `cd` (model habit):** about 1 run in 20–40 still runs `cd <project or scratch dir> && …` for a listing or an inline script; the skill forbids it and the same habit appears at baseline (regression set: candidate 2/27, baseline 4/27). The two discuss-specific forms (cd into `ask/scripts`, scripts that build the request JSON) stopped after b2091df.
- **Stub counter (verifier A5):** `exec-count.txt` in `evals/_harness/stub/codex-stub.py` is a plain read-modify-write; two parallel `by_model` calls could share a number. No case combines `exec.sequence` with `by_model` today.
- **Single API stalls:** two eval runs timed out after one response took about 19 minutes to start (t03 headless-default, reg-final unstructured-ends); not skill behaviour, but cases with 1500 s timeouts are sensitive to it.

**Blocked by:** None — can start immediately.

- [ ] Decide per item: fix (with an offline-proven grader where it is report wording), or accept as a documented residual.

## Comments

- 2026-10-06 — 2249a95: the stub claims each exec call's number by creating `.stub/exec-claim.<n>` exclusively (a test with eight concurrent calls and a widened race window failed on the old read-modify-write counter and passes now; the verifier reproduced 3–5 distinct records of 8 on the old stub, 8 of 8 on the new); the unread `exec-count.txt` is gone. Discussion cases have a 2400 s timeout.
- Accepted residuals (user decision 2026-10-06): report wording drift (self-made labels, counts, recommendation order — the c2 grader now accepts either order) and the occasional bare `cd` (fu2 1/9, baseline habit).
- Environment note from the verifier: on this machine a PowerShell `Get-Process` call took about 4 s on 2026-10-06, which made `run-stop-scripts.test.mjs`, `process-lifecycle.test.mjs` and `consultation_test.py` time out in that session; the diff touches none of run.sh, `_tree.sh` or consult.py, and the same suites passed earlier the same day (consultation_test 37 OK, run-stop-scripts 104/0).
