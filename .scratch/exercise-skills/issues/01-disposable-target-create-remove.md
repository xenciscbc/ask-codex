# 01 — Disposable target: create a copy, remove only what was created

**What to build:** the script can create a disposable target for an exercise and remove it again, as two operations of the existing consultation CLI. Create makes a new, empty directory under a user-confirmed root, copies the project into it without version-control metadata, and records exactly what it created. Remove deletes only that recorded directory, after checking it is still the same directory. Nothing in this ticket starts Codex; it is the safety floor every later ticket builds on (spec: "Disposable target lifecycle", "Request fields"; user stories 11, 15–18, 65; ADR 0009).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

**Plan:** acceptance amended by `../plan.md` rev 6, claim C1 (invariants listed there).

Security-critical (it decides what the exercise writes and what it deletes): needs a security review and an approved plan before any change.

- [ ] Create refuses a root that the request does not mark as confirmed by the user, and refuses any target path that already exists (file, directory, link or junction); nothing is written in either case.
- [ ] Create makes a new directory under the root and copies the project into it; version-control metadata (`.git` and the like) is never copied.
- [ ] Links and junctions in the project are never followed out of the project while copying.
- [ ] A copy that fails (for example on a volume where it cannot be made) fails clearly, removes the partial target it created, and never falls back to the user's working tree.
- [ ] The record of the created target (path plus an identity check) is kept with the user-level run state, never in the project.
- [ ] Remove deletes only the recorded directory; a directory replaced after creation (identity mismatch), a path outside the root, or a missing record is refused and reported, never deleted.
- [ ] Remove never follows a link or junction inside the target out of it (offline test with a junction to a sentinel directory: the sentinel survives).
- [ ] A removal that fails reports the target's location so the user can clean up by hand.
- [ ] Offline tests at Seam 1 (CLI, no Codex) cover each refusal and the removal guards; all existing offline harness tests pass.

## Comments
