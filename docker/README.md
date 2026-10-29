# Local Zammad stack for MCP development

Docker Compose runs a **Zammad instance** next to your machine so you can test the
MCP server without touching production.

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

Open `http://localhost:8080` after 2–3 minutes. Default login:
`admin@example.com` / `admin`.

Create an API token under **Profile → Token Access**, then point your MCP client at
`http://localhost:8080`.

## Choose a Zammad version

Set `ZAMMAD_VERSION` in `.env` (see `.env.example`):

| Tag | Purpose |
| --- | --- |
| `7.2.2-0024` | **Default** — Zammad 7.2.2, current stable |
| `7.2` | Floating 7.2 patch updates |
| `7.1` | Previous stable line |
| `7.0` | Match a 7.0 instance |
| `6.5` | Last supported 6.x line |
| `6.3` | Legacy 6.x checks |

Example:

```env
ZAMMAD_VERSION=7.1
```

The stack follows the current Zammad Docker layout: PostgreSQL 17, Redis 8,
Memcached, Elasticsearch 9, plus the railsserver, websocket, scheduler, and
nginx containers from the Zammad image. The MCP server package itself is the
same for all tags — only the local Zammad containers change.

**Switching versions:** stop the stack and remove volumes. A 7.1 data directory
cannot be reused: the database role layout and the Elasticsearch major version
changed.

```bash
docker compose down -v
docker compose up -d
```

Full compatibility matrix:
[docs/COMPATIBILITY.md](../docs/COMPATIBILITY.md)
