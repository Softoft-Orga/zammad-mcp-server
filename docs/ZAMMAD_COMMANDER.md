# Zammad Commander — browser chat for your helpdesk

**[Zammad Commander](https://github.com/Softoft-Orga/zammad-commander)** is a free,
MIT-licensed Docker Compose stack that connects **[LibreChat](https://www.librechat.ai/)**
(a browser chat UI) to **this MCP server** and **your Zammad instance**. Support leads
and admins get natural-language search, summaries, and reply drafts — without installing
Cursor or Claude Desktop and without granting the AI delete tools.

You bring:

- A running Zammad (**6.0+**, tested with **7.x**) and an API token (**Profile → Token Access**)
- Either an [OpenRouter](https://openrouter.ai/) API key (cloud LLM) **or** local [Ollama](https://ollama.com/) (on-prem LLM)

Commander runs `zammad-mcp-server` as a **Streamable HTTP** sidecar (`/mcp/`). LibreChat
calls the same tools documented in the [Tools Reference](https://openticketai.com/en/docs/zammad-mcp-server/tools/).

## Quick start (recommended)

Clone Commander — not this repo — unless you are hacking on the MCP server itself:

```bash
git clone https://github.com/Softoft-Orga/zammad-commander.git
cd zammad-commander
cp env.example .env
# Edit .env: ZAMMAD_URL, ZAMMAD_HTTP_TOKEN, and LibreChat secrets (see env.example).

# Variant A — cloud LLM (OpenRouter):
docker compose up -d

# Variant B — on-prem LLM (Ollama, builds MCP from GitHub):
docker compose -f docker-compose.yml -f docker-compose.onprem.yml up -d
docker compose -f docker-compose.yml -f docker-compose.onprem.yml \
  exec ollama ollama pull qwen3.6:27b
```

Open **http://localhost:3080**, create a local LibreChat account, and choose the
**Zammad Commander** model preset.

### Try these prompts

1. _"Run a health check on Zammad."_
2. _"List open tickets and flag anything that looks overdue."_
3. _"Summarize ticket #1 for a shift handover."_
4. _"Draft a friendly reply for ticket #1 — don't send it, just show me the draft."_

Full README (hardware sizing, demo Zammad, GCP demo): **[zammad-commander](https://github.com/Softoft-Orga/zammad-commander)**.

## No Zammad yet? Use the bundled demo stack

This repository ships a local Zammad for development in `docker/`:

```bash
git clone https://github.com/Softoft-Orga/zammad-mcp-server.git
cd zammad-mcp-server/docker
docker compose up -d
# Create an admin and API token at http://localhost:8080
```

In **zammad-commander** `.env` (on the host running Docker):

```env
ZAMMAD_URL=http://host.docker.internal:8080
ZAMMAD_HTTP_TOKEN=<token from demo Zammad>
```

Then start Commander as above.

## How Commander uses this MCP server

| Piece | Role |
| --- | --- |
| LibreChat | Chat UI + LLM (OpenRouter or Ollama) |
| `zammad-mcp` service | This project over HTTP — holds one Zammad API token |
| Your Zammad | Ticket system of record |

Default **internal admin** policy (env on the MCP container):

```env
MCP_ALLOWED_CATEGORIES=all
MCP_DENIED_TOOLS=delete_ticket,delete_user,delete_organization
```

Change env to get read-only analysts, scoped groups, or future customer-facing profiles.
See [Access control](../README.md#access-control--security) and
[Configuration](https://openticketai.com/en/docs/zammad-mcp-server/configuration/).

## Commander vs Claude / Cursor

| | Zammad Commander | Claude Desktop / Cursor + `uvx` |
| --- | --- | --- |
| Audience | Admins, support leads | Developers |
| UI | Browser (LibreChat) | Desktop IDE |
| MCP transport | Streamable HTTP (Docker sidecar) | stdio (`uvx zammad-mcp-server`) |
| Setup | `docker compose up` | JSON MCP config |

Both use the **same** MCP tools and access-control env vars.

## Related

- [Zammad Commander repository](https://github.com/Softoft-Orga/zammad-commander)
- [Agent workflows (website)](https://openticketai.com/en/docs/zammad-mcp-server/workflows/)
- [Deployment — Streamable HTTP](DEPLOYMENT.md#docker-deployment)
