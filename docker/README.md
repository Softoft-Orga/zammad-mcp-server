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

Set `ZAMMAD_VERSION` in `.env`:

| Tag | Purpose |
| --- | --- |
| `7.1` | **Default** — current release, primary test target |
| `7.0` | Match a 7.0 instance |
| `6.5` | Last supported 6.x line |
| `6.3` | Legacy 6.x checks |

Example:

```env
ZAMMAD_VERSION=6.5
```

The MCP server package itself is the same for all tags — only the local Zammad
container changes.

**Switching major versions:** stop the stack and remove volumes if migrations fail:

```bash
docker compose down -v
docker compose up -d
```

Full compatibility matrix:
[docs/COMPATIBILITY.md](../docs/COMPATIBILITY.md)
