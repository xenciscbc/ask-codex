# 08 — Parallel consultation

**What to build:** In a manual consultation the user can name two different models, each with an optional effort (e.g. `astra:high, sol`), and receive two independent opinions. Claude runs one background Codex run per model with identical packaging, neither seeing the other's output, and presents a single merged result grouped into consensus, solo claims, and divergences — each claim tagged with its source model and Claude's disposition, and each divergence explaining which side Claude adopts and why. More than two models or the same model twice is refused with a clear message and no Codex call. If one model fails, the other's result is presented normally with a note naming the failed model and reason. Both runs share one timeout timer: at expiry Claude reports which model is done and asks only about the ones still running, holding finished results until everything completes or the user stops the rest. Parallel is manual-only, except when the session-scoped model override names two models. See spec: user stories 36–44, 64.

**Blocked by:** 03 — Model aliases and effort rules; 04 — Failure handling; 07 — Timeout monitoring.

**Status:** ready-for-agent

- [ ] Two distinct models resolve via alias rules, each with its own effort computed by the consultation-effort rules.
- [ ] Two separate background runs with separate temporary directories; identical packaged question.
- [ ] Merged presentation uses the consensus / solo claims / divergences grouping with model tags and dispositions; every divergence has an adoption rationale.
- [ ] Over-limit or duplicate-model requests are refused with no Codex call.
- [ ] Partial failure presents the surviving opinion (without grouping) plus the failure note.
- [ ] Shared timer behaviour as described; no half-result is shown and later revised.
- [ ] Proactive consultations run in parallel only when the session override names two models.
- [ ] Eval cases pass: `astra, sol` → two `codex` calls with `gpt-6-astra`/`medium` and `gpt-5.6-sol`/`high`; divergent stub replies → `llm` grader checks grouping and rationale; three models → zero `codex` calls; one stub run failing → surviving result plus failure note.

## Comments

**2026-09-16 — slice-08 readiness.** Round 1 REVISE (2 blockers) led to: per-model argv graders on `exec-argv.<slug>.json` (full disable set `count:5`, `-s read-only`, `--disable apps`) plus `no-violations`, because two runs in one project would otherwise leave only the last call's argv; and a fixed `Parallel check: done — …; still running — …` line with regex graders and an offline paraphrase test, plus a `--keep-temp` transcript excerpt for case 5 so the verifier can check that no claim is shown before the check. Advisories taken: "one `codex exec` per consultation" becomes "per model"; stdin files must not contain the other model's reply; two temp dirs and two background runs counted; fixed refusal line; a two-model metachar example in the reference token rule. Round 2: READY. Narrowing: proactive two-model parallel (session override naming two models) is written in the skill but not claimed as verified while ticket 05 is paused. Execution starts once ticket 06 is confirmed.
