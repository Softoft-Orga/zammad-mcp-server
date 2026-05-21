# Zammad MCP Server

<!-- mcp-name: io.github.softoft-orga/zammad-mcp-server -->

A powerful, production-ready Model Context Protocol (MCP) server for [Zammad](https://zammad.com) - the open-source helpdesk and ticket system.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/zammad-mcp-server.svg)](https://pypi.org/project/zammad-mcp-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0+-green.svg)](https://github.com/jlowin/fastmcp)

## Overview

The Zammad MCP Server provides AI assistants (like Claude) with structured, type-safe access to Zammad ticket system functionality. Built on the [Model Context Protocol](https://modelcontextprotocol.io/), it enables intelligent ticket management, customer support automation, and helpdesk operations through natural language interactions.

### Key Features

- **Comprehensive API Coverage**: Full access to tickets, users, organizations, groups, and more
- **Advanced Access Control**: Granular permissions with category-based and tool-level restrictions
- **Production-Ready**: Built with FastMCP, Pydantic, and modern Python practices
- **Flexible Authentication**: Supports API tokens, OAuth2, and basic authentication
- **Smart Caching**: Intelligent caching for static data (groups, states, priorities)
- **Type-Safe**: Full Pydantic models with runtime validation
- **Extensible**: Easy to add new tools and integrations
- **Well-Tested**: Comprehensive test suite with 90%+ coverage

## Quick Start

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

We provide a complete Docker Compose setup for local development with Zammad:

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

## Available Tools

The server provides 30+ tools organized into categories:

### Tickets
- `get_ticket` - Get ticket details
- `search_tickets` - Search with filters
- `create_ticket` - Create new tickets
- `update_ticket` - Update ticket properties
- `delete_ticket` - Delete tickets (admin)
- `get_ticket_articles` - Get all messages
- `create_article` - Add responses/notes
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

## Access Control

The server includes a sophisticated access control system:

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

The server supports three authentication methods:

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

## Hosting Options

The server can be hosted in multiple ways:

### 1. Local Development

```bash
zammad-mcp-server
```

### 2. Docker Container

```bash
docker build -t zammad-mcp-server .
docker run -p 8000:8000 -e ZAMMAD_URL=$ZAMMAD_URL zammad-mcp-server
```

### 3. Cloud Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for cloud deployment guides:
- Google Cloud Run
- AWS Lambda
- Railway
- Fly.io

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

- 📖 [Documentation](https://github.com/Softoft-Orga/zammad-mcp-server/tree/main/docs)
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
