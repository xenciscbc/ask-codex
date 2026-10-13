# 01 — Disposable target: create a copy, remove only what was created

**What to build:** the script can create a disposable target for an exercise and remove it again, as two operations of the existing consultation CLI. Create makes a new, empty directory under a user-confirmed root, copies the project into it without version-control metadata, and records exactly what it created. Remove deletes only that recorded directory, after checking it is still the same directory. Nothing in this ticket starts Codex; it is the safety floor every later ticket builds on (spec: "Disposable target lifecycle", "Request fields"; user stories 11, 15–18, 65; ADR 0009).

**Blocked by:** None — can start immediately.

**Status:** resolved — accepted by the user's accept-and-land decision at acc8887 (2026-10-13); code review APPROVED, outcome verification CONFIRMED, Adversarial review HELD missing (U13); see Comments

**Plan:** acceptance amended by `../plan.md` rev 6, claim C1 (invariants listed there).

Security-critical (it decides what the exercise writes and what it deletes): needs a security review and an approved plan before any change.

- [x] Create refuses a root that the request does not mark as confirmed by the user, and refuses any target path that already exists (file, directory, link or junction); nothing is written in either case.
- [x] Create makes a new directory under the root and copies the project into it; version-control metadata (`.git` and the like) is never copied.
- [x] Links and junctions in the project are never followed out of the project while copying.
- [x] A copy that fails (for example on a volume where it cannot be made) fails clearly, removes the partial target it created, and never falls back to the user's working tree.
- [x] The record of the created target (path plus an identity check) is kept with the user-level run state, never in the project.
- [x] Remove deletes only the recorded directory; a directory replaced after creation (identity mismatch), a path outside the root, or a missing record is refused and reported, never deleted.
- [x] Remove never follows a link or junction inside the target out of it (offline test with a junction to a sentinel directory: the sentinel survives).
- [x] A removal that fails reports the target's location so the user can clean up by hand.
- [x] Offline tests at Seam 1 (CLI, no Codex) cover each refusal and the removal guards; all existing offline harness tests pass.

## Comments

- 2026-10-13 — Implemented by security-executor: 00d34ad (create/remove), 3ee4c91 (code review call 1 B1: cloud placeholders exposed and skipped; single handle owner; base checked before creation), df107d5 (verification call 1: `<base>\ask-codex` junction into the project refused; run directory created through verified handles), deb2d10 (verification call 2: local-drive final paths only for project, base and run directory), acc8887 (Adversarial review call 1: directories with a Git repository layout are VCS metadata — project refused, nested skipped and listed, checked after the copy).
- Passes at acc8887: code review APPROVED (call 5; calls 1 CHANGES_REQUESTED, 2–4 APPROVED on fixes), outcome verification CONFIRMED (call 4; calls 1–2 REFUTED, 3 CONFIRMED at deb2d10). Adversarial review: calls 1 and 2 INCONCLUSIVE; call 2 found nothing beyond the gaps below.
- **Accept and land (user decision, 2026-10-13):** C1 accepted at acc8887 without a HELD. Missing: Adversarial review HELD. Remaining risks, untested on this host without administrator rights and covered only by static analysis (U13): case-sensitive directories (including a `HEAD` file masked by a `head` directory when both the project and the confirmed root are case-sensitive), cloud-placeholder simulation (the real OneDrive metadata probe showed placeholders exposed and skipped), 8.3 short names. Also recorded: a root placed under a directory with a bare-repository layout lets Git find that ancestor (the root is user-confirmed; I1 checks only `.git`/`.codex` ancestors). These go to the README residual risks in C7; non-blocking follow-ups are in the handoff record `ui-exercise-c1-followups.md`. Landing on `main` still waits for the user's word.
- Offline: `evals/_harness/exercise_target_test.py` 31 OK (1 skipped: symlink privilege); `resolve_test.py` 42 OK; `consultation_test.py` 39 OK (intermittent full-suite timing failures in unrelated tests are tracked separately).
