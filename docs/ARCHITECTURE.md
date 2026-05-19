# Zammad MCP Server Architecture

This document describes the technical architecture and design decisions of the Zammad MCP Server.

## Overview

The Zammad MCP Server is built on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to provide AI assistants with structured access to Zammad ticket system functionality. It follows a clean, modular architecture with strong type safety and clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client Layer                         │
│                   (Claude Desktop, IDE, etc.)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP Protocol (stdio / SSE)
┌──────────────────────────▼──────────────────────────────────────┐
│                      MCP Server (FastMCP)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Tools     │  │  Resources  │  │        Prompts          │  │
│  │  (30+)      │  │  (3 URI)    │  │       (3 built-in)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Access Control Layer                        │    │
│  │  - Permission levels (DENIED/READ_ONLY/WRITE/ADMIN)     │    │
│  │  - Category-based access                                │    │
│  │  - Tool-level restrictions                              │    │
│  │  - Group/org filtering                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────────────┐
│                     Zammad Client Wrapper                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Auth       │  │   Caching   │  │    Error Handling       │  │
│  │  (3 types)  │  │  (TTLCache) │  │  (Custom exceptions)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Zammad API Instance                        │
│                    (REST API /api/v1)                             │
└───────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Server (`server.py`)

The main server implementation using [FastMCP](https://github.com/jlowin/fastmcp) framework.

**Responsibilities:**
- MCP protocol implementation
- Tool, resource, and prompt registration
- Request routing and response handling
- Global client lifecycle management

**Key Features:**
- 30+ tools for comprehensive Zammad operations
- 3 resources with URI-based access pattern
- 3 pre-configured prompts for common scenarios
- Lifespan management for proper initialization

**Design Patterns:**
- **Dependency Injection**: Shared client instance across all tools
- **Context Managers**: Proper resource cleanup
- **Decorator-Based Registration**: Clean tool definition

### 2. Zammad Client (`client.py`)

A wrapper around HTTP calls providing a clean, type-safe interface.

**Responsibilities:**
- API authentication (token, OAuth2, username/password)
- HTTP request handling with retries
- Response transformation to Pydantic models
- Error handling and custom exceptions

**Key Methods:**

```python
# Ticket operations
ticket = client.get_ticket(ticket_id, include_articles=True)
result = client.search_tickets(query, state, priority, ...)
ticket = client.create_ticket(request)
ticket = client.update_ticket(ticket_id, request)
client.delete_ticket(ticket_id)

# User operations
user = client.get_user(user_id)
result = client.search_users(query, page, per_page)

# Organization operations
org = client.get_organization(org_id)
result = client.search_organizations(query, page, per_page)

# Static data with caching
groups = client.list_groups()
states = client.get_ticket_states()
priorities = client.get_priorities()
```

### 3. Access Control (`access_control.py`)

Sophisticated permission system for controlling tool access.

**Features:**
- Four permission levels: DENIED, READ_ONLY, WRITE, ADMIN
- Category-based permissions (tickets, users, organizations, etc.)
- Tool-level overrides
- Pattern-based denied tools (wildcards)
- Group/organization filtering for read operations
- Access logging for audit trails

**Architecture:**

```python
@dataclass
class AccessPolicy:
    default_permission: Permission
    category_permissions: dict[ToolCategory, Permission]
    tool_permissions: dict[str, Permission]
    denied_tools: set[str]
    allowed_groups: set[str] | None
```

### 4. Data Models (`models.py`)

Comprehensive Pydantic models ensuring type safety and validation.

**Model Hierarchy:**

```
BaseModel
├── Ticket
│   ├── state: StateBrief | str | None
│   ├── priority: PriorityBrief | str | None
│   ├── group: GroupBrief | str | None
│   ├── owner: UserBrief | str | None
│   └── articles: list[Article] | None
├── User
│   └── organization: Organization | None
├── Organization
├── Group
├── Article
│   ├── type: str
│   ├── sender: str
│   └── internal: bool
├── TicketStats
│   └── by_group: dict[str, int]
├── Request Models (for creation/updates)
│   ├── TicketCreateRequest
│   ├── TicketUpdateRequest
│   ├── ArticleCreateRequest
│   ├── UserCreateRequest
│   └── OrganizationCreateRequest
└── Enums
    ├── TicketState
    ├── TicketPriority
    └── ArticleType
```

**Validation Features:**
- Automatic type coercion
- Required field validation
- Extra field handling (`extra = "forbid"`)
- Union types for expanded fields (handles both object and string representations)
- Email validation for user models

## Data Flow

### Tool Execution Flow

1. **Request Reception**: MCP client sends tool invocation
2. **Access Check**: FastMCP validates against tool schema
3. **Permission Validation**: Access controller checks permissions
4. **Client Check**: Ensure Zammad client is initialized
5. **API Call**: Execute Zammad API operation
6. **Filtering**: Apply access control filters to response
7. **Response Transform**: Convert to Pydantic model
8. **MCP Response**: Return structured data to client

### Resource Access Flow

1. **URI Parsing**: Extract entity type and ID from URI
2. **Permission Check**: Verify read access
3. **Direct Fetch**: Retrieve specific entity from Zammad
4. **Model Transform**: Convert to appropriate Pydantic model
5. **Content Generation**: Format for MCP resource response

## Authentication

Supports three authentication methods with precedence:

1. **API Token (Recommended)**
   ```bash
   ZAMMAD_HTTP_TOKEN=your-token
   ```

2. **OAuth2 Token**
   ```bash
   ZAMMAD_OAUTH2_TOKEN=your-oauth-token
   ```

3. **Username/Password**
   ```bash
   ZAMMAD_USERNAME=user
   ZAMMAD_PASSWORD=pass
   ```

**Implementation:**
```python
if self.http_token:
    headers["Authorization"] = f"Token token={self.http_token}"
elif self.oauth2_token:
    headers["Authorization"] = f"Bearer {self.oauth2_token}"
elif self.username and self.password:
    auth = (self.username, self.password)
```

## State Management

### Global Client State

```python
_client: ZammadClient | None = None
_access_controller: AccessController | None = None

def get_client() -> ZammadClient:
    if _client is None:
        raise RuntimeError("Zammad client not initialized")
    return _client
```

### Initialization Lifecycle

```python
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    global _client, _access_controller
    
    # Initialize
    _client = ZammadClient()
    _access_controller = AccessController.from_env()
    
    yield {"client": _client, "access_controller": _access_controller}
    
    # Cleanup
    if _client:
        _client.close()
```

## API Integration Details

### Zammad API Behaviors

1. **Expand Parameter**: When `expand=True` is used:
   - Returns string representations for related objects (e.g., `"group": "Users"`)
   - Does not return full nested objects as might be expected
   - All models use union types to handle both formats:
     ```python
     # Example: Ticket model
     group: GroupBrief | str | None = None
     state: StateBrief | str | None = None
     ```
   - This pattern is applied consistently across all models

2. **Search API**:
   - Uses custom query syntax for filtering
   - Supports field-specific searches (e.g., `state.name:open`)
   - Returns paginated results with metadata

3. **State Handling**: When processing ticket states:
   - Must check if state is a string (expanded) or object (non-expanded)
   - Helper functions extract state names consistently

## Error Handling

### Error Hierarchy

```
ZammadClientError (base)
├── AuthenticationError (401)
├── NotFoundError (404)
└── ZammadClientError (other HTTP errors, network errors)
```

### Error Responses

MCP errors include:
- Error code/type
- Human-readable message
- Optional details object

**Implementation:**
```python
try:
    result = client.get_ticket(ticket_id)
except NotFoundError:
    return {"error": f"Ticket {ticket_id} not found"}
except PermissionError:
    return {"error": "Access denied for this ticket"}
except ZammadClientError as e:
    return {"error": str(e), "status_code": e.status_code}
```

## Performance Considerations

### Current Optimizations

1. **Intelligent Caching**
   - In-memory caching for groups, states, and priorities
   - TTL-based expiration (default: 300 seconds)
   - Reduces repeated API calls for static data
   - Cache invalidation via `clear_caches()` method

2. **Pagination for Statistics**
   - `get_ticket_stats` uses pagination to process tickets in batches
   - Avoids loading entire dataset into memory
   - Configurable safety limit (MAX_PAGES_FOR_TICKET_SCAN)
   - Performance metrics logging

### Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Sync HTTP | Simpler implementation; async can be added later |
| In-memory cache | Fast; suitable for single-instance deployments |
| Pydantic models | Type safety + validation + serialization |
| FastMCP | Modern, actively maintained, decorator-based |

### Remaining Optimization Opportunities

1. **Enhanced Caching**
   - Redis for distributed deployments
   - Longer TTLs for truly static data
   - Cache warming on startup

2. **Connection Pooling**
   ```python
   httpx.Client(
       limits=httpx.Limits(max_keepalive_connections=10)
   )
   ```

3. **Async Implementation**
   - Use `httpx.AsyncClient`
   - Concurrent request handling
   - Better resource utilization under load

## Security Considerations

### Current Security Measures

- Environment variable configuration (no hardcoded secrets)
- No credential logging
- HTTPS enforcement for API calls
- Access control at tool and category level
- Access logging for audit trails
- Input validation via Pydantic models

### Security Best Practices

1. **Input Validation**
   - URL validation to prevent SSRF
   - Input sanitization for user data
   - Parameter bounds checking

2. **Rate Limiting**
   - Client-side rate limiting in access policy
   - Future: Implement request throttling

3. **Audit Logging**
   - Operation logging in access controller
   - Security event tracking
   - Compliance support via structured logging

## Extension Points

### Adding New Tools

1. Define tool function with `@mcp.tool()` decorator
2. Implement using `get_client()`
3. Add access control check
4. Return Pydantic model instance or dict
5. Add tests with mocked client

**Example:**
```python
@mcp.tool()
def my_new_tool(param: str) -> dict[str, Any]:
    """Description of what the tool does."""
    check_access("my_new_tool", Permission.READ_ONLY)
    client = get_client()
    
    result = client.some_operation(param)
    return result.model_dump()
```

### Adding New Resources

1. Define resource handler with URI pattern
2. Parse entity ID from URI
3. Fetch and transform data
4. Return formatted content

**Example:**
```python
@mcp.resource("zammad://myresource/{id}")
def get_my_resource(id: str) -> str:
    """Get resource details."""
    client = get_client()
    data = client.get_something(int(id))
    return f"# Resource {id}\n\n{data.name}"
```

### Adding New Prompts

1. Use `@mcp.prompt()` decorator
2. Define parameters and template
3. Include example usage

**Example:**
```python
@mcp.prompt()
def my_prompt(ticket_id: str) -> str:
    """Generate something useful."""
    return f"Analyze ticket #{ticket_id} and..."
```

## Testing Architecture

### Test Structure

```
tests/
├── conftest.py         # Fixtures and configuration
├── test_models.py      # Model validation tests
├── test_client.py      # Client wrapper tests
├── test_access_control.py  # Permission system tests
└── test_server.py      # Tool integration tests
```

### Test Strategy

- **Unit Tests**: Fast, isolated, use mocks
- **Integration Tests**: Test with real Zammad (Docker)
- **Access Control Tests**: Verify permission enforcement
- **Mock Strategy**: Mock `ZammadClient` for unit tests
- **Coverage Target**: 90%+ overall coverage

### Test Patterns

```python
@pytest.fixture
def sample_ticket() -> Ticket:
    return Ticket.model_validate(create_ticket_data(expand=True))

def test_get_ticket_success(mock_client: MagicMock) -> None:
    mock_client.get_ticket.return_value = sample_ticket()
    result = get_ticket(1)
    assert result["id"] == 1
```

## Configuration Management

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZAMMAD_URL` | Yes | - | Zammad instance URL |
| `ZAMMAD_HTTP_TOKEN` | No* | - | API token |
| `ZAMMAD_OAUTH2_TOKEN` | No* | - | OAuth2 token |
| `ZAMMAD_USERNAME` | No* | - | Basic auth username |
| `ZAMMAD_PASSWORD` | No* | - | Basic auth password |
| `MCP_ALLOWED_CATEGORIES` | No | `all` | Allowed tool categories |
| `MCP_DENIED_TOOLS` | No | - | Denied tools (comma-separated) |
| `MCP_ALLOWED_GROUPS` | No | - | Allowed groups (comma-separated) |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `CACHE_TTL_SECONDS` | No | `300` | Cache TTL |

*At least one authentication method required

### Configuration Precedence

1. Explicit constructor parameters (highest)
2. Environment variables
3. Default values (lowest)

## Deployment Architecture

### Local Development

```
┌──────────────┐
│  Claude App  │
└──────┬───────┘
       │ stdio
┌──────▼───────┐
│  MCP Server  │
└──────┬───────┘
       │ HTTP
┌──────▼───────┐
│    Zammad    │
└──────────────┘
```

### Cloud Deployment (SSE Transport)

```
┌──────────────┐      ┌──────────────┐
│  Claude App  │──────▶│  MCP Server  │
└──────────────┘  SSE  │  (Cloud Run) │
                      └──────┬───────┘
                             │ HTTP
                      ┌──────▼───────┐
                      │    Zammad    │
                      └──────────────┘
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment guides.

## Future Architecture Considerations

### Microservices Pattern

Consider splitting into:
- Core MCP server
- Zammad client service
- Caching service (Redis)
- WebSocket service for real-time updates

### Plugin Architecture

Enable extensions for:
- Custom authentication providers
- Additional ticket sources
- Workflow automation
- Custom prompts/tools

### Scalability

- Horizontal scaling with load balancer
- Distributed caching with Redis
- Message queue for async operations
- Database for audit logs

---

*This architecture is designed to be extensible while maintaining simplicity for the common use case.*
