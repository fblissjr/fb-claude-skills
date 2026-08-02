last updated: 2026-07-21

# analysis index

Most of this directory was deleted on 2026-07-21. What remains is what could not
be regenerated from a maintained source. See `log.md` for the reasoning.

| Document | Why it survived |
|---|---|
| [data_centric_agent_state_research.md](data_centric_agent_state_research.md) | Decision record: the comparative survey and DuckDB-vs-alternatives rationale behind `tools/agent-state`. **The package was retired 2026-08-02** — not because this comparison was wrong, but because the data it would have held turned out to live in files already (see [agent_state_population.md](../internals/agent_state_population.md)). The DuckDB-vs-alternatives reasoning still applies the next time something genuinely needs a local analytical store. Nobody will redo it. |
| [mcp_protocol_and_servers.md](mcp_protocol_and_servers.md) | Verified current, linked from `CLAUDE.md`, describes a stable external spec. |
| [log.md](log.md) | Append-only decision log, including for this deletion. |
