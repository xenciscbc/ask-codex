# Draft additions to evals/_harness/stub/codex-stub.py for ticket 07 (apply once ticket 04 is confirmed).
# Needs `import time` at the top.

# In exec_(), after thread.started / turn.started are emitted and before the other modes:
#
#     if mode == "slow-active":
#         cfg = data.get("exec") or {}
#         every = float(cfg.get("event_every_s", 5))
#         duration = float(cfg.get("duration_s", 100))
#         start = time.monotonic()
#         n = 0
#         while time.monotonic() - start < duration:
#             time.sleep(every)
#             n += 1
#             emit({"type": "item.completed", "item": {"id": f"progress_{n}", "type": "reasoning", "text": f"step {n}"}})
#         # then fall through to the normal valid reply below (mode treated as "valid")
#         mode = "valid"
#     elif mode == "slow-silent":
#         cfg = data.get("exec") or {}
#         time.sleep(float(cfg.get("duration_s", 600)))
#         with open(os.path.join(records, "exec-finished"), "w", encoding="utf-8") as f:
#             f.write("ended by itself\n")
#         sys.stderr.write("Error: stub silent run ended\n")
#         sys.exit(1)
#
# `emit` flushes each line, so events.jsonl (the skill redirects stdout there) gains a line — and a
# fresh mtime — every `event_every_s` seconds. slow-silent writes nothing after turn.started, so the
# file's mtime stays at the start time. Killing the process (TaskStop) leaves no exec-finished file.
# For slow-active, also write exec-finished after the reply so graders can tell a completed run.

# Offline test additions (stub-modes.test.mjs): slow-active with event_every_s 0.2, duration_s 1
# → ≥ 4 progress events then a valid -o file; slow-silent with duration_s 1 → exit 1 and
# exec-finished present; slow-silent with duration_s 30 killed after 1 s → no exec-finished.
