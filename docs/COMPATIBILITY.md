# Zammad compatibility

The Zammad MCP Server connects to Zammad through the **HTTP REST API** only. It does
not install a Zammad plugin or modify your helpdesk. Any Zammad instance that exposes
the API and accepts personal access tokens can be used.

## Supported Zammad versions

| Zammad | MCP server | Notes |
| --- | --- | --- |
| **7.1** | **Tested** (primary) | Current default in the bundled `docker/` dev stack. PostgreSQL required on the Zammad side. Coexists with Zammad native AI. |
| **7.0** | **Tested** | Same REST API surface as 7.1. PostgreSQL required. |
| **6.5 – 6.5.x** | **Compatible** | Security fixes still published for 6.5.x. MySQL or PostgreSQL on the Zammad side. |
| **6.0 – 6.4.x** | **Compatible** | Minimum supported major line. Prefer 6.5+ if you stay on Zammad 6. |
| **&lt; 6.0** | **Not supported** | API and token behaviour differ; not validated. |

**Managed Zammad (zammad.com hosting):** supported when your plan includes API token
access — the MCP server only needs `ZAMMAD_URL` and a token.

## MCP server vs Zammad version

The **PyPI package** (`zammad-mcp-server`) is versioned independently (currently
`0.1.x`). One MCP server release works across all supported Zammad versions above;
you do not need a different MCP build per Zammad minor release.

| Artifact | Versioning |
| --- | --- |
| `zammad-mcp-server` on PyPI | Semver (`0.1.1`, …) — MCP tools and client behaviour |
| Bundled dev stack (`docker/`) | `ZAMMAD_VERSION` env var — which Zammad image to run locally |
| Your production Zammad | Whatever you already run — point `ZAMMAD_URL` at it |

## Pick a Zammad version in the dev stack

The local Docker Compose stack reads `ZAMMAD_VERSION` from `docker/.env`:

```bash
cd docker
cp .env.example .env
# edit ZAMMAD_VERSION if needed (default: 7.1)
docker compose up -d
```

Supported image tags for local development:

| `ZAMMAD_VERSION` | Use when |
| --- | --- |
| `7.1` | Default — matches current Zammad release (recommended) |
| `7.0` | Reproduce a 7.0 instance before upgrading |
| `6.5` | Test against the last 6.x line |
| `6.3` | Legacy 6.x smoke tests |

**Important:** Changing `ZAMMAD_VERSION` on an existing volume may require removing
old volumes first (`docker compose down -v`) because major upgrades are handled by
Zammad's own migration path, not by this compose file.

## Zammad-side requirements

| Topic | Zammad 6.x | Zammad 7.x |
| --- | --- | --- |
| Database | MySQL or PostgreSQL | **PostgreSQL only** |
| API auth | Personal access token (recommended), OAuth2, or basic auth | Same |
| Elasticsearch | Required for search-heavy MCP workflows | Required |

## Verify connectivity

After configuring `ZAMMAD_URL` and `ZAMMAD_HTTP_TOKEN`, run the MCP tool
`health_check`, then `get_server_info` to read the connected Zammad version from your
instance.

## Reporting issues

When filing a bug, include:

- `zammad-mcp-server` version (`pip show zammad-mcp-server`)
- Zammad version (from **Admin → System** or `get_server_info`)
- Whether the instance is self-hosted or managed
