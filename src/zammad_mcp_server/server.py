"""Zammad MCP Server implementation using FastMCP."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
from fastmcp import FastMCP, Context

from zammad_mcp_server.access_control import AccessController, Permission
from zammad_mcp_server.client import ZammadClient, ZammadClientError, NotFoundError
from zammad_mcp_server.models import (
    ArticleCreateRequest,
    GroupCreateRequest,
    OrganizationCreateRequest,
    TicketCreateRequest,
    TicketUpdateRequest,
    UserCreateRequest,
)

logger = structlog.get_logger()

# Global state
_client: ZammadClient | None = None
_access_controller: AccessController | None = None


def get_client() -> ZammadClient:
    """Get the global Zammad client."""
    if _client is None:
        raise RuntimeError("Zammad client not initialized")
    return _client


def get_access_controller() -> AccessController:
    """Get the global access controller."""
    if _access_controller is None:
        raise RuntimeError("Access controller not initialized")
    return _access_controller


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage application lifecycle."""
    global _client, _access_controller

    # Initialize
    try:
        _client = ZammadClient()
        _access_controller = AccessController.from_env()

        logger.info(
            "server_initialized",
            url=_client.url,
            allowed_tools=len(_access_controller.get_allowed_tools()),
        )

        yield {"client": _client, "access_controller": _access_controller}

    except Exception as e:
        logger.error("initialization_failed", error=str(e))
        raise

    finally:
        # Cleanup
        if _client:
            _client.close()
            logger.info("client_closed")


# Create FastMCP instance
mcp = FastMCP(
    "Zammad MCP Server",
    lifespan=app_lifespan,
)


# Helper function to check access
def check_access(tool_name: str, required_permission: Permission) -> None:
    """Check if access is allowed for a tool."""
    controller = get_access_controller()
    allowed = False

    if required_permission == Permission.ADMIN:
        allowed = controller.can_admin(tool_name)
    elif required_permission == Permission.WRITE:
        allowed = controller.can_write(tool_name)
    elif required_permission == Permission.READ_ONLY:
        allowed = controller.can_read(tool_name)

    controller.log_access(tool_name, allowed)

    if not allowed:
        raise PermissionError(f"Access denied for tool: {tool_name}")


# ==================== System Tools ====================

@mcp.tool()
def health_check() -> dict[str, Any]:
    """Check the health of the Zammad MCP Server and its connection to Zammad.

    Returns:
        Health status information including server status and connection details.
    """
    check_access("health_check", Permission.READ_ONLY)
    client = get_client()

    zammad_health = client.health_check()

    return {
        "mcp_server": "healthy",
        "zammad_connection": zammad_health,
        "allowed_tools_count": len(get_access_controller().get_allowed_tools()),
    }


@mcp.tool()
def get_server_info() -> dict[str, Any]:
    """Get information about the Zammad server.

    Returns:
        Server version, configuration, and status information.
    """
    check_access("get_server_info", Permission.READ_ONLY)
    client = get_client()
    return client.get_server_info()


@mcp.tool()
def get_allowed_tools() -> list[dict[str, str]]:
    """Get a list of all tools accessible to the current session.

    Returns:
        List of tools with their categories and permission levels.
    """
    check_access("get_allowed_tools", Permission.READ_ONLY)
    controller = get_access_controller()
    return controller.get_tool_info()


# ==================== Ticket Tools ====================

@mcp.tool()
def get_ticket(
    ticket_id: int,
    include_articles: bool = False,
) -> dict[str, Any]:
    """Get a specific ticket by ID.

    Args:
        ticket_id: The ID of the ticket to retrieve
        include_articles: Whether to include all articles/messages in the ticket

    Returns:
        Ticket details including metadata and optionally articles.
    """
    check_access("get_ticket", Permission.READ_ONLY)
    client = get_client()

    try:
        ticket = client.get_ticket(ticket_id, include_articles=include_articles)

        # Apply access control filtering
        ticket_dict = ticket.model_dump()
        filtered = get_access_controller().filter_ticket(ticket_dict)

        if filtered is None:
            raise PermissionError("Access denied for this ticket")

        return filtered
    except NotFoundError:
        return {"error": f"Ticket {ticket_id} not found"}


@mcp.tool()
def search_tickets(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    group: str | None = None,
    owner: str | None = None,
    customer: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Search for tickets with various filters.

    Args:
        query: Full-text search query
        state: Filter by ticket state (e.g., 'open', 'closed', 'new')
        priority: Filter by priority (e.g., '1 low', '2 normal', '3 high')
        group: Filter by group name
        owner: Filter by owner email
        customer: Filter by customer email
        page: Page number for pagination
        per_page: Number of results per page (max 100)

    Returns:
        Search results with tickets and pagination info.
    """
    check_access("search_tickets", Permission.READ_ONLY)
    client = get_client()
    controller = get_access_controller()

    result = client.search_tickets(
        query=query,
        state=state,
        priority=priority,
        group=group,
        owner=owner,
        customer=customer,
        page=page,
        per_page=min(per_page, 100),
    )

    # Apply access control filtering
    filtered_items = []
    for item in result.items:
        ticket_dict = item.model_dump() if hasattr(item, 'model_dump') else item
        filtered = controller.filter_ticket(ticket_dict)
        if filtered:
            filtered_items.append(filtered)

    return {
        "tickets": filtered_items,
        "total_count": len(filtered_items),
        "page": page,
        "per_page": per_page,
        "total_pages": (len(filtered_items) + per_page - 1) // per_page,
    }


@mcp.tool()
def create_ticket(
    title: str,
    group: str,
    customer: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    article_subject: str | None = None,
    article_body: str | None = None,
    article_type: str = "note",
    article_internal: bool = False,
) -> dict[str, Any]:
    """Create a new ticket.

    Args:
        title: Ticket title/subject
        group: Group to assign the ticket to
        customer: Customer email or login
        state: Initial state (default: 'new')
        priority: Priority level (e.g., '1 low', '2 normal', '3 high')
        article_subject: Subject for the initial article
        article_body: Body text for the initial article
        article_type: Type of article (note, email, phone, web)
        article_internal: Whether the article is internal only

    Returns:
        The created ticket details.
    """
    check_access("create_ticket", Permission.WRITE)
    client = get_client()

    from zammad_mcp_server.models import TicketCreateRequest, ArticleType

    # Validate article type
    try:
        article_type_enum = ArticleType(article_type)
    except ValueError:
        article_type_enum = ArticleType.NOTE

    request = TicketCreateRequest(
        title=title,
        group=group,
        customer=customer,
        state=state,  # type: ignore
        priority=priority,  # type: ignore
        article_subject=article_subject,
        article_body=article_body,
        article_type=article_type_enum,
        article_internal=article_internal,
    )

    ticket = client.create_ticket(request)
    return ticket.model_dump()


@mcp.tool()
def update_ticket(
    ticket_id: int,
    title: str | None = None,
    group: str | None = None,
    owner: str | None = None,
    state: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    """Update an existing ticket.

    Args:
        ticket_id: The ID of the ticket to update
        title: New title for the ticket
        group: New group to assign the ticket to
        owner: New owner (email or login)
        state: New state (e.g., 'open', 'closed', 'pending reminder')
        priority: New priority level

    Returns:
        The updated ticket details.
    """
    check_access("update_ticket", Permission.WRITE)
    client = get_client()

    from zammad_mcp_server.models import TicketUpdateRequest, TicketState, TicketPriority

    # Validate state and priority
    state_enum = None
    if state:
        try:
            state_enum = TicketState(state)
        except ValueError:
            pass

    priority_enum = None
    if priority:
        try:
            priority_enum = TicketPriority(priority)
        except ValueError:
            pass

    request = TicketUpdateRequest(
        title=title,
        group=group,
        owner=owner,
        state=state_enum,
        priority=priority_enum,
    )

    ticket = client.update_ticket(ticket_id, request)
    return ticket.model_dump()


@mcp.tool()
def delete_ticket(ticket_id: int) -> dict[str, Any]:
    """Delete a ticket.

    Args:
        ticket_id: The ID of the ticket to delete

    Returns:
        Success status.
    """
    check_access("delete_ticket", Permission.ADMIN)
    client = get_client()

    try:
        client.delete_ticket(ticket_id)
        return {"success": True, "message": f"Ticket {ticket_id} deleted"}
    except NotFoundError:
        return {"success": False, "error": f"Ticket {ticket_id} not found"}


@mcp.tool()
def get_ticket_articles(ticket_id: int) -> dict[str, Any]:
    """Get all articles (messages) for a ticket.

    Args:
        ticket_id: The ID of the ticket

    Returns:
        List of articles in the ticket.
    """
    check_access("get_ticket_articles", Permission.READ_ONLY)
    client = get_client()

    try:
        articles = client.get_ticket_articles(ticket_id)
        return {
            "ticket_id": ticket_id,
            "articles": [a.model_dump() for a in articles],
            "count": len(articles),
        }
    except NotFoundError:
        return {"error": f"Ticket {ticket_id} not found"}


@mcp.tool()
def create_article(
    ticket_id: int,
    body: str,
    subject: str | None = None,
    type: str = "note",
    internal: bool = False,
    to: str | None = None,
    cc: str | None = None,
    time_unit: float | None = None,
    time_accounting_type_id: int | None = None,
) -> dict[str, Any]:
    """Add a new article to an existing ticket.

    Args:
        ticket_id: The ID of the ticket to add the article to
        body: The content of the article
        subject: Subject line for the article
        type: Type of article (note, email, phone, web)
        internal: Whether this is an internal-only note
        to: Recipient email (for email type)
        cc: CC recipients (for email type)
        time_unit: Optional time to book in the unit configured in Zammad
            (for example minutes). On instances configured for minutes, pass
            60 for one hour. Booked as a time accounting entry linked to the
            new article.
        time_accounting_type_id: Optional time accounting type id

    Returns:
        The created article details.
    """
    check_access("create_article", Permission.WRITE)
    client = get_client()

    from zammad_mcp_server.models import ArticleCreateRequest, ArticleType

    try:
        article_type_enum = ArticleType(type)
    except ValueError:
        article_type_enum = ArticleType.NOTE

    request = ArticleCreateRequest(
        ticket_id=ticket_id,
        body=body,
        subject=subject,
        type=article_type_enum,
        internal=internal,
        to=to,
        cc=cc,
        time_unit=time_unit,
        time_accounting_type_id=time_accounting_type_id,
    )

    article = client.create_article(request)
    return article.model_dump()


@mcp.tool()
def create_time_accounting(
    ticket_id: int,
    time_unit: float,
    type_id: int | None = None,
    article_id: int | None = None,
) -> dict[str, Any]:
    """Book a time accounting entry on a ticket.

    Args:
        ticket_id: The ID of the ticket to book time on
        time_unit: Amount of time in the unit configured in Zammad (for
            example minutes). On instances configured for minutes, pass 60
            for one hour.
        type_id: Optional time accounting type id
        article_id: Optional article to link the time entry to

    Returns:
        The created time accounting entry.
    """
    check_access("create_time_accounting", Permission.WRITE)
    client = get_client()
    return client.create_time_accounting(
        ticket_id=ticket_id,
        time_unit=time_unit,
        type_id=type_id,
        ticket_article_id=article_id,
    )


@mcp.tool()
def get_time_accountings(ticket_id: int) -> dict[str, Any]:
    """Get all time accounting entries booked on a ticket.

    Args:
        ticket_id: The ID of the ticket

    Returns:
        The list of time accounting entries and their total.
    """
    check_access("get_time_accountings", Permission.READ_ONLY)
    client = get_client()
    entries = client.get_time_accountings(ticket_id)

    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    total = sum(_to_float(e.get("time_unit")) for e in entries)
    return {
        "ticket_id": ticket_id,
        "entries": entries,
        "count": len(entries),
        "total_time_unit": total,
    }


@mcp.tool()
def get_ticket_stats(
    group: str | None = None,
    max_scan_pages: int = 10,
) -> dict[str, Any]:
    """Get ticket statistics.

    Args:
        group: Filter by specific group (optional)
        max_scan_pages: Maximum pages to scan for large datasets

    Returns:
        Ticket statistics including counts by state, group, and priority.
    """
    check_access("get_ticket_stats", Permission.READ_ONLY)
    client = get_client()

    stats = client.get_ticket_stats(group=group, max_scan_pages=max_scan_pages)
    return stats.model_dump()


@mcp.tool()
def get_ticket_states() -> list[dict[str, Any]]:
    """Get all available ticket states.

    Returns:
        List of available ticket states with their properties.
    """
    check_access("get_ticket_states", Permission.READ_ONLY)
    client = get_client()
    return client.get_ticket_states()


@mcp.tool()
def get_priorities() -> list[dict[str, Any]]:
    """Get all available ticket priorities.

    Returns:
        List of available priority levels.
    """
    check_access("get_priorities", Permission.READ_ONLY)
    client = get_client()
    return client.get_priorities()


# ==================== User Tools ====================

@mcp.tool()
def get_user(user_id: int) -> dict[str, Any]:
    """Get a user by ID.

    Args:
        user_id: The ID of the user

    Returns:
        User details.
    """
    check_access("get_user", Permission.READ_ONLY)
    client = get_client()

    try:
        user = client.get_user(user_id)
        return user.model_dump()
    except NotFoundError:
        return {"error": f"User {user_id} not found"}


@mcp.tool()
def search_users(
    query: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Search for users.

    Args:
        query: Search query (email, name, etc.)
        page: Page number
        per_page: Results per page (max 100)

    Returns:
        Search results with users.
    """
    check_access("search_users", Permission.READ_ONLY)
    client = get_client()

    result = client.search_users(
        query=query,
        page=page,
        per_page=min(per_page, 100),
    )

    return {
        "users": [u.model_dump() for u in result.items],
        "total_count": result.total_count,
        "page": page,
        "per_page": per_page,
    }


@mcp.tool()
def create_user(
    email: str | None = None,
    firstname: str | None = None,
    lastname: str | None = None,
    login: str | None = None,
    phone: str | None = None,
    mobile: str | None = None,
    organization: str | None = None,
    password: str | None = None,
    active: bool = True,
) -> dict[str, Any]:
    """Create a new user.

    Args:
        email: User's email address
        firstname: First name
        lastname: Last name
        login: Login username (defaults to email if not provided)
        phone: Phone number
        mobile: Mobile number
        organization: Organization name
        password: Initial password
        active: Whether the user is active

    Returns:
        The created user details.
    """
    check_access("create_user", Permission.WRITE)
    client = get_client()

    request = UserCreateRequest(
        email=email,
        firstname=firstname,
        lastname=lastname,
        login=login,
        phone=phone,
        mobile=mobile,
        organization=organization,
        password=password,
        active=active,
    )

    user = client.create_user(request)
    return user.model_dump()


@mcp.tool()
def update_user(
    user_id: int,
    login: str | None = None,
    firstname: str | None = None,
    lastname: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    mobile: str | None = None,
    organization: str | None = None,
    active: bool | None = None,
) -> dict[str, Any]:
    """Update a user.

    Args:
        user_id: The ID of the user to update
        login: New login name
        firstname: New first name
        lastname: New last name
        email: New email address
        phone: New phone number
        mobile: New mobile number
        organization: New organization name
        active: Whether the user is active

    Returns:
        The updated user details.
    """
    check_access("update_user", Permission.WRITE)
    client = get_client()

    updates = {
        k: v
        for k, v in {
            "login": login,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone": phone,
            "mobile": mobile,
            "organization": organization,
            "active": active,
        }.items()
        if v is not None
    }

    user = client.update_user(user_id, **updates)
    return user.model_dump()


@mcp.tool()
def delete_user(user_id: int) -> dict[str, Any]:
    """Delete a user.

    Args:
        user_id: The ID of the user to delete

    Returns:
        Success status.
    """
    check_access("delete_user", Permission.ADMIN)
    client = get_client()

    try:
        client.delete_user(user_id)
        return {"success": True, "message": f"User {user_id} deleted"}
    except NotFoundError:
        return {"success": False, "error": f"User {user_id} not found"}


@mcp.tool()
def get_current_user() -> dict[str, Any]:
    """Get the currently authenticated user.

    Returns:
        Current user details.
    """
    check_access("get_current_user", Permission.READ_ONLY)
    client = get_client()

    user = client.get_current_user()
    return user.model_dump()


# ==================== Organization Tools ====================

@mcp.tool()
def get_organization(org_id: int) -> dict[str, Any]:
    """Get an organization by ID.

    Args:
        org_id: The ID of the organization

    Returns:
        Organization details.
    """
    check_access("get_organization", Permission.READ_ONLY)
    client = get_client()

    try:
        org = client.get_organization(org_id)
        return org.model_dump()
    except NotFoundError:
        return {"error": f"Organization {org_id} not found"}


@mcp.tool()
def search_organizations(
    query: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Search for organizations.

    Args:
        query: Search query
        page: Page number
        per_page: Results per page (max 100)

    Returns:
        Search results with organizations.
    """
    check_access("search_organizations", Permission.READ_ONLY)
    client = get_client()

    result = client.search_organizations(
        query=query,
        page=page,
        per_page=min(per_page, 100),
    )

    return {
        "organizations": [o.model_dump() for o in result.items],
        "total_count": result.total_count,
        "page": page,
        "per_page": per_page,
    }


@mcp.tool()
def create_organization(
    name: str,
    shared: bool = True,
    note: str | None = None,
    domain: str | None = None,
    active: bool = True,
) -> dict[str, Any]:
    """Create a new organization.

    Args:
        name: Organization name
        shared: Whether tickets are shared within the organization
        note: Internal note about the organization
        domain: Email domain for automatic assignment
        active: Whether the organization is active

    Returns:
        The created organization details.
    """
    check_access("create_organization", Permission.WRITE)
    client = get_client()

    request = OrganizationCreateRequest(
        name=name,
        shared=shared,
        note=note,
        domain=domain,
        active=active,
    )

    org = client.create_organization(request)
    return org.model_dump()


@mcp.tool()
def update_organization(
    org_id: int,
    name: str | None = None,
    shared: bool | None = None,
    note: str | None = None,
    domain: str | None = None,
    active: bool | None = None,
) -> dict[str, Any]:
    """Update an organization.

    Args:
        org_id: The ID of the organization to update
        name: New organization name
        shared: Whether the organization is shared
        note: New note text
        domain: New domain
        active: Whether the organization is active

    Returns:
        The updated organization details.
    """
    check_access("update_organization", Permission.WRITE)
    client = get_client()

    updates = {
        k: v
        for k, v in {
            "name": name,
            "shared": shared,
            "note": note,
            "domain": domain,
            "active": active,
        }.items()
        if v is not None
    }

    org = client.update_organization(org_id, **updates)
    return org.model_dump()


@mcp.tool()
def delete_organization(org_id: int) -> dict[str, Any]:
    """Delete an organization.

    Args:
        org_id: The ID of the organization to delete

    Returns:
        Success status.
    """
    check_access("delete_organization", Permission.ADMIN)
    client = get_client()

    try:
        client.delete_organization(org_id)
        return {"success": True, "message": f"Organization {org_id} deleted"}
    except NotFoundError:
        return {"success": False, "error": f"Organization {org_id} not found"}


# ==================== Group Tools ====================

@mcp.tool()
def get_group(group_id: int) -> dict[str, Any]:
    """Get a group by ID.

    Args:
        group_id: The ID of the group

    Returns:
        Group details.
    """
    check_access("get_group", Permission.READ_ONLY)
    client = get_client()

    try:
        group = client.get_group(group_id)
        return group.model_dump()
    except NotFoundError:
        return {"error": f"Group {group_id} not found"}


@mcp.tool()
def list_groups() -> dict[str, Any]:
    """List all groups.

    Returns:
        List of all groups.
    """
    check_access("list_groups", Permission.READ_ONLY)
    client = get_client()

    groups = client.list_groups()
    return {
        "groups": [g.model_dump() for g in groups],
        "count": len(groups),
    }


@mcp.tool()
def create_group(
    name: str,
    active: bool = True,
    note: str | None = None,
) -> dict[str, Any]:
    """Create a new group.

    Args:
        name: Group name
        active: Whether the group is active
        note: Internal note about the group

    Returns:
        The created group details.
    """
    check_access("create_group", Permission.WRITE)
    client = get_client()

    request = GroupCreateRequest(name=name, active=active, note=note)
    group = client.create_group(request)
    return group.model_dump()


# ==================== Resources ====================

@mcp.resource("zammad://ticket/{ticket_id}")
def get_ticket_resource(ticket_id: str) -> str:
    """Get ticket details as a formatted resource."""
    check_access("get_ticket", Permission.READ_ONLY)
    client = get_client()

    try:
        ticket = client.get_ticket(int(ticket_id), include_articles=True)

        lines = [
            f"# Ticket #{ticket.number or ticket.id}: {ticket.title}",
            "",
            f"**State:** {ticket.get_state_name() or 'Unknown'}",
            f"**Priority:** {ticket.get_priority_name() or 'Unknown'}",
            f"**Group:** {ticket.get_group_name() or 'Unknown'}",
            f"**Created:** {ticket.created_at}",
            "",
            "## Articles",
            "",
        ]

        if ticket.articles:
            for article in ticket.articles:
                lines.extend([
                    f"### {article.subject or 'No subject'} ({article.type or 'unknown'})",
                    f"*From: {article.from_address or 'Unknown'} | Internal: {article.internal}*",
                    "",
                    article.body or "No content",
                    "",
                    "---",
                    "",
                ])
        else:
            lines.append("No articles available.")

        return "\n".join(lines)
    except NotFoundError:
        return f"Ticket {ticket_id} not found."


@mcp.resource("zammad://user/{user_id}")
def get_user_resource(user_id: str) -> str:
    """Get user details as a formatted resource."""
    check_access("get_user", Permission.READ_ONLY)
    client = get_client()

    try:
        user = client.get_user(int(user_id))

        return f"""# User: {user.get_full_name()}

**Email:** {user.email or 'N/A'}
**Login:** {user.login or 'N/A'}
**Phone:** {user.phone or 'N/A'}
**Mobile:** {user.mobile or 'N/A'}
**Active:** {user.active}
**Created:** {user.created_at}
"""
    except NotFoundError:
        return f"User {user_id} not found."


@mcp.resource("zammad://config/states")
def get_states_resource() -> str:
    """Get available ticket states as a resource."""
    check_access("get_ticket_states", Permission.READ_ONLY)
    client = get_client()

    states = client.get_ticket_states()

    lines = ["# Available Ticket States", ""]
    for state in states:
        name = state.get("name", "Unknown")
        state_type = state.get("stateType", state.get("state_type", "Unknown"))
        lines.append(f"- **{name}** (Type: {state_type})")

    return "\n".join(lines)


# ==================== Prompts ====================

@mcp.prompt()
def ticket_summary_prompt(ticket_id: str) -> str:
    """Generate a summary of a ticket."""
    return f"""Please analyze ticket #{ticket_id} and provide a comprehensive summary including:

1. What is the main issue or request?
2. What is the current status?
3. What actions have been taken so far?
4. Who are the key participants?
5. What are the next steps or recommendations?

Use the available tools to fetch the ticket details and articles."""


@mcp.prompt()
def customer_communication_prompt(
    ticket_id: str,
    tone: str = "professional",
) -> str:
    """Generate a customer communication draft."""
    return f"""Draft a {tone} response for ticket #{ticket_id}.

Please:
1. Review the ticket history and understand the context
2. Address all customer questions or concerns
3. Provide clear next steps or resolution
4. Maintain a {tone} tone throughout

Use the ticket tools to gather information before drafting the response."""


@mcp.prompt()
def escalation_analysis_prompt(ticket_id: str) -> str:
    """Analyze if a ticket needs escalation."""
    return f"""Analyze ticket #{ticket_id} for escalation potential:

1. How long has the ticket been open?
2. How many interactions have occurred?
3. Is the customer showing signs of frustration?
4. Does this issue require specialized expertise?
5. What is the business impact?

Provide a recommendation on whether to escalate, to whom, and why."""


# ==================== Main Entry Point ====================

def main() -> None:
    """Run the MCP server."""
    import asyncio

    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger.info("starting_mcp_server")
    mcp.run()


if __name__ == "__main__":
    main()
