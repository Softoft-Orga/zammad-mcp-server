"""Test fixtures and configuration for Zammad MCP Server tests."""

import os
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response

# Set test environment variables before importing
os.environ["ZAMMAD_URL"] = "http://test-zammad.local"
os.environ["ZAMMAD_HTTP_TOKEN"] = "test-token"

from zammad_mcp_server.access_control import AccessController, AccessPolicy, Permission, ToolCategory
from zammad_mcp_server.client import ZammadClient
from zammad_mcp_server.models import (
    Article,
    Group,
    GroupBrief,
    Organization,
    PriorityBrief,
    StateBrief,
    Ticket,
    User,
    UserBrief,
)


# ============== Fixture Factories ==============

def create_ticket_data(
    ticket_id: int = 1,
    title: str = "Test Ticket",
    state: str = "open",
    priority: str = "2 normal",
    group: str = "Users",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a ticket data dictionary for testing."""
    return {
        "id": ticket_id,
        "number": f"#{ticket_id:06d}",
        "title": title,
        "state": state if kwargs.get("expand", False) else {"id": 2, "name": state, "stateType": "open"},
        "priority": priority if kwargs.get("expand", False) else {"id": 2, "name": priority},
        "group": group if kwargs.get("expand", False) else {"id": 1, "name": group},
        "owner": kwargs.get("owner", {"id": 1, "firstname": "Agent", "lastname": "User", "email": "agent@test.com"}),
        "customer": kwargs.get("customer", {"id": 2, "firstname": "Customer", "lastname": "User", "email": "customer@test.com"}),
        "articleCount": kwargs.get("article_count", 3),
        "createdAt": kwargs.get("created_at", datetime.now().isoformat()),
        "updatedAt": kwargs.get("updated_at", datetime.now().isoformat()),
        **kwargs,
    }


def create_user_data(
    user_id: int = 1,
    email: str = "user@test.com",
    firstname: str = "Test",
    lastname: str = "User",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a user data dictionary for testing."""
    return {
        "id": user_id,
        "login": kwargs.get("login", email),
        "email": email,
        "firstname": firstname,
        "lastname": lastname,
        "phone": kwargs.get("phone"),
        "mobile": kwargs.get("mobile"),
        "organization": kwargs.get("organization"),
        "roleIds": kwargs.get("role_ids", [1, 2]),
        "active": kwargs.get("active", True),
        "createdAt": kwargs.get("created_at", datetime.now().isoformat()),
        "updatedAt": kwargs.get("updated_at", datetime.now().isoformat()),
        **kwargs,
    }


def create_article_data(
    article_id: int = 1,
    ticket_id: int = 1,
    body: str = "Test article content",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create an article data dictionary for testing."""
    return {
        "id": article_id,
        "ticketId": ticket_id,
        "type": kwargs.get("type", "note"),
        "sender": kwargs.get("sender", "Agent"),
        "subject": kwargs.get("subject", "Test Subject"),
        "body": body,
        "from": kwargs.get("from_address", "agent@test.com"),
        "to": kwargs.get("to"),
        "cc": kwargs.get("cc"),
        "internal": kwargs.get("internal", False),
        "createdAt": kwargs.get("created_at", datetime.now().isoformat()),
        "createdBy": kwargs.get("created_by", {"id": 1, "firstname": "Agent", "lastname": "User"}),
        **kwargs,
    }


def create_organization_data(
    org_id: int = 1,
    name: str = "Test Organization",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create an organization data dictionary for testing."""
    return {
        "id": org_id,
        "name": name,
        "shared": kwargs.get("shared", True),
        "note": kwargs.get("note"),
        "active": kwargs.get("active", True),
        "domain": kwargs.get("domain"),
        "memberIds": kwargs.get("member_ids", [1, 2, 3]),
        "createdAt": kwargs.get("created_at", datetime.now().isoformat()),
        "updatedAt": kwargs.get("updated_at", datetime.now().isoformat()),
        **kwargs,
    }


# ============== Pytest Fixtures ==============

@pytest.fixture
def mock_zammad_client() -> MagicMock:
    """Create a mock Zammad client."""
    client = MagicMock(spec=ZammadClient)
    client.url = "http://test-zammad.local"
    client.http_token = "test-token"
    return client


@pytest.fixture
def sample_ticket() -> Ticket:
    """Create a sample Ticket model instance."""
    return Ticket.model_validate(create_ticket_data(expand=True))


@pytest.fixture
def sample_user() -> User:
    """Create a sample User model instance."""
    return User.model_validate(create_user_data())


@pytest.fixture
def sample_article() -> Article:
    """Create a sample Article model instance."""
    return Article.model_validate(create_article_data())


@pytest.fixture
def sample_organization() -> Organization:
    """Create a sample Organization model instance."""
    return Organization.model_validate(create_organization_data())


@pytest.fixture
def sample_group() -> Group:
    """Create a sample Group model instance."""
    return Group.model_validate({
        "id": 1,
        "name": "Users",
        "active": True,
        "userIds": [1, 2, 3],
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
    })


@pytest.fixture
def unrestricted_policy() -> AccessPolicy:
    """Create an unrestricted access policy."""
    return AccessPolicy(
        default_permission=Permission.WRITE,
        category_permissions={
            ToolCategory.ALL: Permission.WRITE,
        },
    )


@pytest.fixture
def read_only_policy() -> AccessPolicy:
    """Create a read-only access policy."""
    return AccessPolicy(
        default_permission=Permission.READ_ONLY,
        category_permissions={
            ToolCategory.TICKETS: Permission.READ_ONLY,
            ToolCategory.USERS: Permission.READ_ONLY,
            ToolCategory.ORGANIZATIONS: Permission.READ_ONLY,
            ToolCategory.GROUPS: Permission.READ_ONLY,
            ToolCategory.ADMIN: Permission.DENIED,
            ToolCategory.SYSTEM: Permission.READ_ONLY,
        },
    )


@pytest.fixture
def restricted_policy() -> AccessPolicy:
    """Create a restricted access policy with specific limitations."""
    return AccessPolicy(
        default_permission=Permission.READ_ONLY,
        category_permissions={
            ToolCategory.TICKETS: Permission.READ_ONLY,
            ToolCategory.USERS: Permission.DENIED,
            ToolCategory.ORGANIZATIONS: Permission.DENIED,
            ToolCategory.GROUPS: Permission.READ_ONLY,
            ToolCategory.ADMIN: Permission.DENIED,
        },
        denied_tools={"delete_ticket"},
        allowed_groups={"Users", "Support"},
    )


@pytest.fixture
def unrestricted_controller(unrestricted_policy: AccessPolicy) -> AccessController:
    """Create an unrestricted access controller."""
    return AccessController(unrestricted_policy)


@pytest.fixture
def read_only_controller(read_only_policy: AccessPolicy) -> AccessController:
    """Create a read-only access controller."""
    return AccessController(read_only_policy)


@pytest.fixture
def restricted_controller(restricted_policy: AccessPolicy) -> AccessController:
    """Create a restricted access controller."""
    return AccessController(restricted_policy)


@pytest.fixture
def zammad_client() -> ZammadClient:
    """Create a real Zammad client for integration tests."""
    return ZammadClient()


@pytest.fixture
def mock_httpx_client() -> MagicMock:
    """Create a mock HTTPX client."""
    return MagicMock(spec=httpx.Client)


# ============== Respx Routes Fixture ==============

@pytest.fixture
def zammad_api_mock(respx_mock: respx.MockRouter) -> respx.MockRouter:
    """Setup common Zammad API mock routes."""
    base_url = "http://test-zammad.local/api/v1"

    # Health check
    respx_mock.get(f"{base_url}/ping").mock(
        return_value=Response(200, json={"version": "6.0.0", " pong": "pong"})
    )

    # Server info
    respx_mock.get(f"{base_url}/system/").mock(
        return_value=Response(200, json={
            "version": "6.0.0",
            "product_name": "Zammad",
            "settings": {},
        })
    )

    # Ticket routes
    respx_mock.get(url__startswith=f"{base_url}/tickets/").mock(
        return_value=Response(200, json=create_ticket_data(expand=True))
    )

    respx_mock.get(url__startswith=f"{base_url}/tickets/search").mock(
        return_value=Response(200, json={
            "tickets": [create_ticket_data(id=i, expand=True) for i in range(1, 4)],
            "tickets_count": 3,
        })
    )

    respx_mock.post(f"{base_url}/tickets").mock(
        return_value=Response(201, json=create_ticket_data(id=999, expand=True))
    )

    respx_mock.put(url__startswith=f"{base_url}/tickets/").mock(
        return_value=Response(200, json=create_ticket_data(id=1, title="Updated", expand=True))
    )

    respx_mock.delete(url__startswith=f"{base_url}/tickets/").mock(
        return_value=Response(200, json={})
    )

    # User routes
    respx_mock.get(url__startswith=f"{base_url}/users/").mock(
        return_value=Response(200, json=create_user_data(expand=True))
    )

    respx_mock.get(url__startswith=f"{base_url}/users/search").mock(
        return_value=Response(200, json={
            "users": [create_user_data(id=i) for i in range(1, 4)],
            "users_count": 3,
        })
    )

    respx_mock.post(f"{base_url}/users").mock(
        return_value=Response(201, json=create_user_data(id=999))
    )

    # Organization routes
    respx_mock.get(url__startswith=f"{base_url}/organizations/").mock(
        return_value=Response(200, json=create_organization_data())
    )

    respx_mock.get(url__startswith=f"{base_url}/organizations/search").mock(
        return_value=Response(200, json={
            "organizations": [create_organization_data(id=i) for i in range(1, 4)],
            "organizations_count": 3,
        })
    )

    respx_mock.post(f"{base_url}/organizations").mock(
        return_value=Response(201, json=create_organization_data(id=999))
    )

    # Group routes
    respx_mock.get(url__startswith=f"{base_url}/groups").mock(
        return_value=Response(200, json=[{
            "id": 1,
            "name": "Users",
            "active": True,
            "userIds": [1, 2, 3],
        }])
    )

    # Ticket states
    respx_mock.get(f"{base_url}/ticket_states").mock(
        return_value=Response(200, json={
            "ticket_states": [
                {"id": 1, "name": "new", "stateType": "new"},
                {"id": 2, "name": "open", "stateType": "open"},
                {"id": 3, "name": "closed", "stateType": "closed"},
            ]
        })
    )

    # Priorities
    respx_mock.get(f"{base_url}/ticket_priorities").mock(
        return_value=Response(200, json={
            "ticket_priorities": [
                {"id": 1, "name": "1 low"},
                {"id": 2, "name": "2 normal"},
                {"id": 3, "name": "3 high"},
            ]
        })
    )

    # Article routes
    respx_mock.get(url__startswith=f"{base_url}/ticket_articles/by_ticket/").mock(
        return_value=Response(200, json={
            "ticket_articles": [create_article_data(id=i) for i in range(1, 4)]
        })
    )

    respx_mock.post(f"{base_url}/ticket_articles").mock(
        return_value=Response(201, json=create_article_data(id=999))
    )

    return respx_mock


# ============== Pytest Configuration ==============

def pytest_configure(config: Any) -> None:
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (requires real Zammad)"
    )


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Modify test collection."""
    # Skip integration tests by default
    skip_integration = pytest.mark.skip(reason="Integration test - requires real Zammad")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
