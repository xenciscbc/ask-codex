# Draft additions to evals/_harness/stub/codex-stub.py for ticket 04 (apply after slice-04 READY).

# 1) In main(), before dispatch — emulate a missing Codex CLI for every invocation:
#
#     if os.environ.get("EVAL_CODEX_STUB_MODE") == "missing":
#         scenario = load_scenario(os.getcwd())
#         if scenario:
#             append(os.path.join(stub_dir(scenario), "missing-calls.log"), " ".join(argv) + "\n")
#         sys.stderr.write("codex: command not found\n")
#         sys.exit(127)
#
#    (load_scenario(os.getcwd()) finds no scenario for the neutral temp dir; the attempt is then
#    only visible in the trace, which is what the CODEX_CALL grader counts.)

# 2) In exec_(), next to the existing failure modes (after turn.started is emitted):
#
#     if mode == "os-error":
#         # Mirrors the observed real failure on a drive where the Windows sandbox cannot run.
#         sys.stdout.write("Error: 功能錯誤。 (os error 1)\n")
#         sys.stdout.flush()
#         sys.exit(1)
#     if mode == "unreadable":
#         emit({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 0}})
#         if opts.get("out"):
#             open(opts["out"], "w", encoding="utf-8").close()
#         return
#
#    Note: sys.stdout on Windows may not be UTF-8; write bytes via sys.stdout.buffer to be safe:
#         sys.stdout.buffer.write("Error: 功能錯誤。 (os error 1)\n".encode("utf-8"))

# 3) Docstring: list the new modes and the EVAL_CODEX_STUB_MODE variable.
