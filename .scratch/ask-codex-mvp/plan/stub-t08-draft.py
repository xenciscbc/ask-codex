# Draft additions to evals/_harness/stub/codex-stub.py for ticket 08 (apply once slice 08 is READY
# and ticket 06 is confirmed).

# 1) In exec_(), right after `data = scenario["data"]`: merge a per-model block chosen by -m.
#
#     slug = opts.get("model")
#     base = dict(data.get("exec") or {})
#     by_model = base.pop("by_model", {}) or {}
#     cfg = {**base, **by_model.get(slug, {})} if slug in by_model else base
#
#    and use `cfg` wherever the code reads `(data.get("exec") or {})` today (mode, reply,
#    event_every_s, duration_s, and the slow-active exec-finished check).

# 2) Records: keep the existing single-run files (other tickets' graders read them) and add per-model
#    copies when -m is given; the sentinel is appended so two calls leave two lines.
#
#     with open(os.path.join(records, "exec.sentinel"), "a", encoding="utf-8") as f:
#         f.write(datetime.datetime.now(datetime.timezone.utc).isoformat() + "\n")
#     for name, payload in (("exec-argv", json.dumps(args, indent=2)), ("exec-stdin", prompt)):
#         ext = "json" if name == "exec-argv" else "txt"
#         with open(os.path.join(records, f"{name}.{ext}"), "w", encoding="utf-8") as f:
#             f.write(payload)
#         if slug:
#             with open(os.path.join(records, f"{name}.{slug}.{ext}"), "w", encoding="utf-8") as f:
#                 f.write(payload)
#
#    slow-silent / slow-active also write `exec-finished.<slug>` next to `exec-finished` when -m is given.

# 3) Docstring: document exec.by_model and the per-model record files.

# Offline test additions (stub-modes.test.mjs): two exec calls in one project with -m gpt-6-astra and
# -m gpt-5.6-sol and a by_model scenario (sol mode fail) → astra exits 0 with its own reply, sol exits 1;
# both exec-argv.<slug>.json and exec-stdin.<slug>.txt exist with the right -m; exec.sentinel has two
# lines; a call without -m still writes only the single-run files.
