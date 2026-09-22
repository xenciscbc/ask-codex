# MCP configuration race — unresolved

Investigation date: 2026-09-22. CLI probed: 0.154.0.

`policy.resolve` enumerates servers and checks a set of per-name disabling overrides. `consult.run` later starts a separate `codex exec`, which reloads configuration. A server introduced between those operations is absent from the disabling overrides. An allowed server can also change its definition. Rechecking immediately before launch only narrows this window.

The race follows from the separate loads; an end-to-end exploit against a live consultation was not run. The following configuration-only probes do not constitute a completed fix:

- Repeated `-c mcp_servers=[] -c 'mcp_servers={...}'` does **not** clear inherited servers. A native `mcp list` probe with existing user servers retained them alongside the new entry. An empty-base probe and a stub that applied each override directly to inherited config misleadingly suggested otherwise; that implementation and its tests were removed.
- `mcp list` / `mcp get` are display projections, not complete replayable definitions. `app-server` `config/read` can return additional security and authentication fields, but obtaining a complete snapshot alone does not force a later `exec` to use it exclusively.
- `exec --ignore-user-config` preserves the authentication home but changes ordinary settings and does not by itself suppress every other configuration layer. The existing [MCP policy ADR](adr/0003-mcp-policy.md) also records a Windows sandbox regression with this flag.
- An isolated `CODEX_HOME` changes authentication lookup. Copying only `auth.json` does not establish compatibility with keyring-backed authentication.

The versioned [Codex loader](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/config/src/loader/mod.rs) builds and merges configuration layers; [exec](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/exec/src/lib.rs) creates its own configuration. A complete remediation needs a supported runtime/configuration isolation boundary, with real inherited-config and authentication tests. Do not treat a merged CLI table or a successful stub-only snapshot test as that boundary.

The current mitigation remains preflight validation and avoiding configuration/plugin changes during preparation and execution. This is an operational precaution, not protection against an adversary who can mutate those sources concurrently.
