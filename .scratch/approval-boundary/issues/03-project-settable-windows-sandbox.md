# 03 — A trusted project can choose the Windows sandbox implementation

Status: needs-triage

Found during ticket 01's adversarial review (static reading of the 0.159.3 binary; not probed): the `[windows] sandbox` key (`elevated`, `unelevated`, `mxc`) is not on the project-layer denylist, so a trusted project's `.codex/config.toml` may select a weaker Windows sandbox implementation for a consultation. Pre-existing; unrelated to the approval fix. Details stay in untracked notes.

- [ ] Confirm whether a project-level `[windows] sandbox` value takes effect under the consultation command line.
- [ ] If it does, pin the implementation on the command line (as ADR 0008/0010 do) or document the risk.

## Comments
