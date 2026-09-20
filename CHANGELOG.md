# Changelog

## 0.2.0

- CLI: `--transport stdio|http|sse` with `MCP_TRANSPORT`, host, port, and path.
- Docker default is Streamable HTTP on port 8000; SSE remains a legacy override.
- Healthcheck uses a TCP listen probe (FastMCP has no `/health` route).
- Access control lists only registered tools (no ghost search tools).
- Tags, attachments, ticket links/merge, and `summarize_ticket`.
- Write-scope enforcement for `MCP_ALLOWED_GROUPS` / `MCP_ALLOWED_ORGANIZATIONS`.
- `MCP_DEFAULT_PERMISSION=read_only`, rate limits, JSON audit log on stderr/file.
- HTML-to-plain article bodies (`MCP_STRIP_HTML`, default on).
- Extra MCP prompts and resources.

## 0.1.1

- Production-ready MCP tools for Zammad 6.0+ / 7.x (tested on 7.1).
- PyPI (`uvx zammad-mcp-server`) and GHCR Docker publish.
