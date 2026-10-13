# 04 — Hardening: model slugs starting with '-', and config errors in the event stream

Status: needs-triage

Two hardening notes from ticket 01's verification and adversarial review (pre-existing, not exploitable by repository content as far as checked):

1. The model-slug patterns in `consult.py` and `models.py` accept a value that starts with `-`. A slug comes from the user's own config or request, not from the consulted repository; how Codex's CLI parser treats such a value after `-m` was not tested.
2. Codex reports configuration warnings and errors as `type:"error"` items in the `--json` event stream, not on stderr. A check that scans only stderr (as ticket 01's live check e did) can miss them; the recorded runs had none in either place.

- [ ] Reject slugs starting with `-` in `models.py`/`consult.py`, with an offline test.
- [ ] Decide whether consultations should surface `type:"error"` event items to Claude.

## Comments
