# Zammad MCP Server — Connect Claude, Cursor & LLMs to Your Zammad Helpdesk

<!-- mcp-name: io.github.softoft-orga/zammad-mcp-server -->

**Zammad MCP Server** is a free, open-source, production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for [Zammad](https://zammad.com), the open-source helpdesk and ticket system. It connects AI assistants — **Claude Desktop**, **Cursor**, and any MCP-compatible LLM agent — directly to your Zammad instance, so you can search tickets, summarize threads, draft replies, and manage users and organizations in natural language.

[![PyPI version](https://img.shields.io/pypi/v/zammad-mcp-server.svg "zammad-mcp-server on PyPI")](https://pypi.org/project/zammad-mcp-server/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg "Requires Python 3.11 or newer")](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg "MIT licensed open-source project")](https://opensource.org/licenses/MIT)
[![Built with FastMCP](https://img.shields.io/badge/FastMCP-2.0+-green.svg "Built on the FastMCP framework")](https://github.com/jlowin/fastmcp)
[![Zammad 6.0+ and 7.x](https://img.shields.io/badge/Zammad-6.0%2B%20%7C%207.x-blue.svg "Compatible with Zammad 6.0+ and 7.x")](docs/COMPATIBILITY.md)

> **In one line:** `uvx zammad-mcp-server` turns your Zammad helpdesk into a set of typed tools any AI agent can call — no Zammad plugin, no custom REST glue code.

> ⭐ **Find this useful?** [Star the repo](https://github.com/Softoft-Orga/zammad-mcp-server) — it helps other Zammad teams discover the project and shapes the [roadmap](#roadmap).

## Table of Contents

- [Overview](#overview)
- [Why use the Zammad MCP Server?](#why-use-the-zammad-mcp-server)
- [Key features](#key-features)
- [Zammad compatibility](#zammad-compatibility)
- [Documentation](#documentation)
- [Quick start](#quick-start)
- [Available MCP tools](#available-mcp-tools)
- [Access control & security](#access-control--security)
- [Authentication methods](#authentication-methods)
- [Architecture](#architecture)
- [Hosting & deployment options](#hosting-options)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Zammad MCP Server gives AI assistants like Claude **structured, type-safe access** to Zammad ticket system functionality over the [Model Context Protocol](https://modelcontextprotocol.io/) — an open standard for connecting LLMs to external tools and data. Instead of scraping the UI or pasting ticket text into a chat window, the assistant calls discrete, validated tools (`search_tickets`, `get_ticket_articles`, `create_article`, and 30+ more) and gets clean, schema-checked data back.

This enables AI-powered ticket management, customer-support automation, and helpdesk reporting through natural-language interactions — while keeping your data on **your** Zammad instance and **your** MCP client.

## Why use the Zammad MCP Server?

Connecting a large language model to a real helpdesk usually means writing a bespoke Zammad REST integration, handling authentication, and reinventing access control before you get a single useful answer. This server removes that friction:

- **Talk to your helpdesk from Claude or Cursor** — "Summarize ticket 4821", "List open tickets in the Support queue", "Draft a reply to this customer."
- **Triage and reporting** — let an agent classify, prioritize, and summarize incoming tickets, or pull `get_ticket_stats` for analytics.
- **Safe by default** — granular, environment-driven access control lets you ship read-only or deny destructive tools (`delete_ticket`, `delete_user`) in production.
- **One integration, every client** — write to MCP once and it works across Claude Desktop, Cursor, and custom agent stacks.
- **No vendor lock-in** — MIT-licensed, self-hosted, and works with any Zammad 6.0+ / 7.x instance via the REST API (no Zammad-side plugin required).

## Key features

- **Comprehensive API Coverage**: Full access to tickets, users, organizations, groups, and more
- **Advanced Access Control**: Granular permissions with category-based and tool-level restrictions
- **Production-Ready**: Built with FastMCP, Pydantic, and modern Python practices
- **Flexible Authentication**: Supports API tokens, OAuth2, and basic authentication
- **Smart Caching**: Intelligent caching for static data (groups, states, priorities)
- **Type-Safe**: Full Pydantic models with runtime validation
- **Extensible**: Easy to add new tools and integrations
- **Well-Tested**: Comprehensive test suite with 90%+ coverage

## Zammad compatibility

The MCP server talks to Zammad through the **REST API**. No Zammad-side plugin is
required. Full matrix: **[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)**.

| Zammad version | Status |
| --- | --- |
| **7.1** | **Tested** (primary; default dev stack) |
| **7.0** | **Tested** |
| **6.5.x** | **Compatible** |
| **6.0 – 6.4.x** | **Compatible** (minimum supported line) |
| **&lt; 6.0** | Not supported |

**MCP package vs Zammad:** `zammad-mcp-server` on PyPI is versioned independently
(`0.1.x`). One MCP release works with every supported Zammad version — set
`ZAMMAD_URL` to your instance; no per-Zammad MCP build.

**Local dev stack:** `docker/` ships Zammad **7.1** by default. Override with
`ZAMMAD_VERSION` in `docker/.env` (`7.0`, `6.5`, `6.3` also supported). See
[docker/README.md](docker/README.md).

Zammad **7.x** requires **PostgreSQL** on the Zammad side (MySQL is not supported
from 7.0 onward). The bundled dev stack uses PostgreSQL.

## Documentation

Full guides, security checklists, and deployment notes live on the Open Ticket AI website:

| Page | What you will learn |
| --- | --- |
| [Zammad MCP Server (overview)](https://openticketai.com/en/docs/zammad-mcp-server/) | Who it is for and how it fits the Zammad + AI landscape |
| [Quick Start](https://openticketai.com/en/docs/zammad-mcp-server/quick-start/) | Install and run `health_check` in minutes |
| [Claude & Cursor Setup](https://openticketai.com/en/docs/zammad-mcp-server/claude-cursor/) | MCP client configuration |
| [Configuration](https://openticketai.com/en/docs/zammad-mcp-server/configuration/) | Environment variables and access policies |
| [Tools Reference](https://openticketai.com/en/docs/zammad-mcp-server/tools/) | All MCP tools by category |
| [Security](https://openticketai.com/en/docs/zammad-mcp-server/security/) | Tokens, least privilege, production checklist |
| [Deployment](https://openticketai.com/en/docs/zammad-mcp-server/deployment/) | Docker, SSE, and production notes |
| [Zammad compatibility (GitHub)](docs/COMPATIBILITY.md) | Supported Zammad versions and dev-stack tags |

**Tutorial:** [Zammad MCP Server — setup and usage (blog)](https://openticketai.com/en/docs/blog/zammad-mcp-server-setup-and-usage/)

**Deutsch:** [Zammad MCP Server Dokumentation](https://openticketai.com/de/docs/zammad-mcp-server/) · [Einrichtung und Nutzung (Blog)](https://openticketai.com/de/docs/blog/zammad-mcp-server-einrichtung-und-nutzung/)

### How this fits the Zammad + AI landscape

- **[Zammad 7.1 native AI](https://openticketai.com/en/docs/blog/zammad-ai-zammad-7-ki-funktionen-leitfaden/)** — built-in summaries and writing assistant inside the Zammad UI.
- **Zammad MCP Server (this project)** — connects **external** MCP clients (Claude Desktop, Cursor, custom agents) to Zammad.
- **[Open Ticket AI Runtime](https://openticketai.com/en/docs/otai-runtime/)** — on-prem inference with **custom-trained** models via the OTAI Zammad connector ([integration guide](https://openticketai.com/en/docs/blog/integrating-zammad-open-ticket-ai/)).

All three can coexist. MCP is the fastest path to “talk to my helpdesk from Claude.” Need custom models on your queues? See [Open Ticket AI for Zammad](https://openticketai.com/en/solutions/zammad/).

## Quick Start

> Step-by-step walkthrough: [Quick Start guide](https://openticketai.com/en/docs/zammad-mcp-server/quick-start/)

### Installation

**From PyPI (recommended for MCP clients):**

```bash
pip install zammad-mcp-server
# or
uv tool install zammad-mcp-server
# or run once without installing
uvx zammad-mcp-server
```

**From source (development):**

```bash
git clone https://github.com/Softoft-Orga/zammad-mcp-server.git
cd zammad-mcp-server
uv sync --extra dev
```

### Configuration

See the [Configuration guide](https://openticketai.com/en/docs/zammad-mcp-server/configuration/) for all environment variables and access policies.

Create a `.env` file:

```env
ZAMMAD_URL=https://your-zammad-instance.com
ZAMMAD_HTTP_TOKEN=your_api_token_here

# Optional: Access control
MCP_ALLOWED_CATEGORIES=all
MCP_DENIED_TOOLS=delete_ticket,delete_user
```

### Running the Server

```bash
# Run with stdio transport (for Claude Desktop)
zammad-mcp-server

# Run with SSE transport (for remote clients)
zammad-mcp-server --transport sse --port 8000
```

### Claude Desktop / Cursor

Full client setup: [Claude & Cursor Setup](https://openticketai.com/en/docs/zammad-mcp-server/claude-cursor/)

Add to `claude_desktop_config.json` or Cursor **Settings → MCP**:

```json
{
  "mcpServers": {
    "zammad": {
      "command": "uvx",
      "args": ["zammad-mcp-server"],
      "env": {
        "ZAMMAD_URL": "https://your-zammad-instance.com",
        "ZAMMAD_HTTP_TOKEN": "your_token",
        "MCP_DENIED_TOOLS": "delete_ticket,delete_user,delete_organization"
      }
    }
  }
}
```

Restart the app after saving. Ask: *"Run health_check on Zammad"* or *"List open tickets."*

## Development Environment

We provide a complete Docker Compose setup for local development. Default: Zammad
**7.1**; set `ZAMMAD_VERSION` in `docker/.env` for other supported tags — see
[docker/README.md](docker/README.md).

```bash
cd docker
docker-compose up -d

# Wait for services to start (may take 2-3 minutes)
docker-compose ps

# Access Zammad at http://localhost:8080
# Default credentials: admin@example.com / admin
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=zammad_mcp_server --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

## Available MCP tools

The server provides 30+ MCP tools for Zammad, organized into categories. Full reference: [Tools Reference](https://openticketai.com/en/docs/zammad-mcp-server/tools/)

### Tickets
- `get_ticket` - Get ticket details
- `search_tickets` - Search with filters
- `create_ticket` - Create new tickets
- `update_ticket` - Update ticket properties
- `delete_ticket` - Delete tickets (admin)
- `get_ticket_articles` - Get all messages
- `create_article` - Add responses/notes (optional `time_unit` books linked time accounting)
- `create_time_accounting` - Book time on a ticket (unit as configured in Zammad, e.g. minutes)
- `get_time_accountings` - List booked time entries and their total for a ticket
- `get_ticket_stats` - Analytics and metrics
- `get_ticket_states` - List available states
- `get_priorities` - List priority levels

### Users
- `get_user` - Get user details
- `search_users` - Find users
- `create_user` - Add new users
- `update_user` - Modify user properties
- `delete_user` - Remove users (admin)
- `get_current_user` - Get authenticated user

### Organizations
- `get_organization` - Get organization details
- `search_organizations` - Find organizations
- `create_organization` - Add organizations
- `update_organization` - Modify organizations
- `delete_organization` - Remove organizations (admin)

### Groups
- `get_group` - Get group details
- `list_groups` - List all groups

### System
- `health_check` - Check server health
- `get_server_info` - Get Zammad version/info
- `get_allowed_tools` - List accessible tools

## Access control & security

The server includes a sophisticated access control system so you can safely connect AI agents to production Zammad. Production checklist: [Security guide](https://openticketai.com/en/docs/zammad-mcp-server/security/)

### Permission Levels

- **DENIED** - Tool completely inaccessible
- **READ_ONLY** - Can view but not modify
- **WRITE** - Can read and modify data
- **ADMIN** - Full access including deletion

### Configuration via Environment Variables

```env
# Allow all categories (default)
MCP_ALLOWED_CATEGORIES=all

# Allow specific categories only
MCP_ALLOWED_CATEGORIES=tickets,groups,system

# Deny specific dangerous tools
MCP_DENIED_TOOLS=delete_ticket,delete_user,delete_organization

# Restrict to specific groups
MCP_ALLOWED_GROUPS=Support,Sales
```

### Programmatic Access Control

```python
from zammad_mcp_server.access_control import AccessController, AccessPolicy, Permission, ToolCategory

# Create custom policy
policy = AccessPolicy(
    default_permission=Permission.READ_ONLY,
    category_permissions={
        ToolCategory.TICKETS: Permission.WRITE,
        ToolCategory.ADMIN: Permission.DENIED,
    },
    denied_tools={"delete_ticket"},
)

controller = AccessController(policy)
```

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical documentation.

```
┌─────────────────┐     ┌─────────────────┐
│  Claude/AI      │     │  MCP Client     │
│  Assistant      │────▶│  (Claude App)   │
└─────────────────┘     └────────┬────────┘
                                 │ MCP Protocol
                        ┌────────▼────────┐
                        │   MCP Server    │
                        │  (FastMCP)      │
                        ├─────────────────┤
                        │  Access Control │
                        │  Tools          │
                        │  Resources      │
                        └────────┬────────┘
                                 │ HTTP/REST
                        ┌────────▼────────┐
                        │  Zammad Client  │
                        │  Wrapper        │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Zammad API     │
                        │   Instance      │
                        └─────────────────┘
```

## Authentication Methods

The server supports three authentication methods. Details: [Configuration — authentication](https://openticketai.com/en/docs/zammad-mcp-server/configuration/)

### 1. API Token (Recommended)

```env
ZAMMAD_HTTP_TOKEN=your_token_here
```

Create tokens in Zammad: **Profile** → **Token Access**

### 2. OAuth2 Token

```env
ZAMMAD_OAUTH2_TOKEN=your_oauth_token
```

### 3. Username/Password

```env
ZAMMAD_USERNAME=admin@example.com
ZAMMAD_PASSWORD=your_password
```

## Resources

The server exposes several MCP resources:

- `zammad://ticket/{id}` - Formatted ticket with articles
- `zammad://user/{id}` - User details
- `zammad://config/states` - Available ticket states

## Prompts

Built-in prompts for common workflows:

- `ticket_summary_prompt` - Generate ticket summaries
- `customer_communication_prompt` - Draft customer responses
- `escalation_analysis_prompt` - Analyze escalation needs

## Hosting options

The Zammad MCP Server can be hosted in multiple ways:

### 1. Local Development

```bash
zammad-mcp-server
```

### 2. Docker Container

Published images are on **GitHub Container Registry** (`ghcr.io`):

```bash
docker pull ghcr.io/softoft-orga/zammad-mcp-server:latest

docker run -p 8000:8000 \
  -e ZAMMAD_URL=https://your-zammad.com \
  -e ZAMMAD_HTTP_TOKEN=your_token \
  ghcr.io/softoft-orga/zammad-mcp-server:latest
```

Build locally:

```bash
docker build -t zammad-mcp-server .
docker run -p 8000:8000 -e ZAMMAD_URL=$ZAMMAD_URL zammad-mcp-server
```

### 3. Cloud Deployment

See the [Deployment guide](https://openticketai.com/en/docs/zammad-mcp-server/deployment/) for Docker, SSE, and production hosting (Google Cloud Run, Railway, Fly.io, and more).

## FAQ

### What is the Zammad MCP Server?

It is an open-source [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes your [Zammad](https://zammad.com) helpdesk as typed tools for AI assistants. Any MCP client (Claude Desktop, Cursor, or a custom agent) can then read and act on Zammad tickets, users, and organizations in natural language.

### How do I connect Claude or Cursor to Zammad?

Install the package and add it to your MCP client config with `ZAMMAD_URL` and `ZAMMAD_HTTP_TOKEN`. The fastest path is `uvx zammad-mcp-server` — see [Quick start](#quick-start) and the [Claude & Cursor setup guide](https://openticketai.com/en/docs/zammad-mcp-server/claude-cursor/).

### Which Zammad versions are supported?

Zammad **7.1** (primary, tested), **7.0** (tested), and **6.0–6.5.x** (compatible). It talks to Zammad over the REST API, so **no Zammad-side plugin is required**. See the [compatibility matrix](docs/COMPATIBILITY.md).

### Is it safe to use on a production Zammad instance?

Yes. Access is controlled by environment variables — restrict categories (`MCP_ALLOWED_CATEGORIES`), deny destructive tools (`MCP_DENIED_TOOLS=delete_ticket,delete_user`), or run fully read-only. Follow the [Security guide](https://openticketai.com/en/docs/zammad-mcp-server/security/) before going live.

### Is the Zammad MCP Server free and open source?

Yes — it is MIT-licensed and free to self-host. There is no SaaS dependency; your ticket data stays on your Zammad instance and your MCP client.

### How is this different from Zammad's built-in AI?

Zammad 7.1's native AI adds summaries and a writing assistant inside the Zammad UI. The Zammad MCP Server instead connects **external** AI agents to Zammad. See [how it fits the Zammad + AI landscape](#how-this-fits-the-zammad--ai-landscape).

### Can I run it with Docker?

Yes — see [Hosting options](#hosting-options) and the [Deployment guide](https://openticketai.com/en/docs/zammad-mcp-server/deployment/) for Docker, SSE, and cloud hosting (Cloud Run, Railway, Fly.io).

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Roadmap

- [ ] WebSocket support for real-time updates
- [ ] Ticket subscription and notification system
- [ ] Advanced search with Elasticsearch integration
- [ ] Multi-tenant support
- [ ] Audit logging
- [ ] Custom tool plugins
- [ ] GraphQL API support
- [ ] Webhook integration

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📖 [Documentation (EN)](https://openticketai.com/en/docs/zammad-mcp-server/) · [Dokumentation (DE)](https://openticketai.com/de/docs/zammad-mcp-server/)
- 📘 [Setup tutorial (blog)](https://openticketai.com/en/docs/blog/zammad-mcp-server-setup-and-usage/)
- 🐛 [Issue Tracker](https://github.com/Softoft-Orga/zammad-mcp-server/issues)
- 💬 [Discussions](https://github.com/Softoft-Orga/zammad-mcp-server/discussions)

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) by James Lowin
- Inspired by the [Model Context Protocol](https://modelcontextprotocol.io/)
- [Zammad](https://zammad.com) - The amazing open-source helpdesk

## Related Projects

- [Zammad](https://github.com/zammad/zammad) - The ticket system itself
- [zammad-py](https://github.com/joeirimpan/zammad-py) - Python client library

---

Made with ❤️ by [Open Ticket AI](https://openticketai.com)
