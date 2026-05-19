"""Tests for Zammad MCP Server client."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from httpx import Response

from zammad_mcp_server.client import (
    ZammadClient,
    ZammadClientError,
    AuthenticationError,
    NotFoundError,
)
from zammad_mcp_server.models import (
    TicketCreateRequest,
    UserCreateRequest,
    OrganizationCreateRequest,
    ArticleCreateRequest,
)


class TestZammadClientInitialization:
    """Test suite for ZammadClient initialization."""

    def test_init_with_env_vars(self, monkeypatch: Any) -> None:
        """Test client initialization from environment variables."""
        monkeypatch.setenv("ZAMMAD_URL", "http://test.local")
        monkeypatch.setenv("ZAMMAD_HTTP_TOKEN", "test-token")

        client = ZammadClient()
        assert client.url == "http://test.local"
        assert client.http_token == "test-token"

    def test_init_with_explicit_params(self) -> None:
        """Test client initialization with explicit parameters."""
        client = ZammadClient(
            url="http://explicit.local",
            http_token="explicit-token",
        )
        assert client.url == "http://explicit.local"
        assert client.http_token == "explicit-token"

    def test_init_without_url_raises(self, monkeypatch: Any) -> None:
        """Test that missing URL raises an error."""
        monkeypatch.delenv("ZAMMAD_URL", raising=False)

        with pytest.raises(ValueError, match="Zammad URL is required"):
            ZammadClient()

    def test_auth_method_token(self) -> None:
        """Test token authentication method detection."""
        client = ZammadClient(
            url="http://test.local",
            http_token="token123",
        )
        assert client._get_auth_method() == "http_token"

    def test_auth_method_oauth2(self) -> None:
        """Test OAuth2 authentication method detection."""
        client = ZammadClient(
            url="http://test.local",
            oauth2_token="oauth123",
        )
        assert client._get_auth_method() == "oauth2"

    def test_auth_method_basic(self) -> None:
        """Test basic authentication method detection."""
        client = ZammadClient(
            url="http://test.local",
            username="user",
            password="pass",
        )
        assert client._get_auth_method() == "basic_auth"


class TestZammadClientRequests:
    """Test suite for ZammadClient HTTP requests."""

    def test_health_check_success(self, zammad_api_mock: Any) -> None:
        """Test successful health check."""
        client = ZammadClient()
        result = client.health_check()

        assert result["status"] == "healthy"
        assert "response" in result

    def test_get_ticket(self, zammad_api_mock: Any) -> None:
        """Test getting a ticket."""
        client = ZammadClient()
        ticket = client.get_ticket(1)

        assert ticket.id == 1
        assert ticket.title is not None

    def test_get_ticket_not_found(self, respx_mock: respx.MockRouter) -> None:
        """Test getting a non-existent ticket."""
        respx_mock.get("http://test-zammad.local/api/v1/tickets/999").mock(
            return_value=Response(404)
        )

        client = ZammadClient()
        with pytest.raises(NotFoundError):
            client.get_ticket(999)

    def test_get_ticket_with_articles(self, respx_mock: respx.MockRouter) -> None:
        """Test getting a ticket with articles."""
        respx_mock.get("http://test-zammad.local/api/v1/tickets/1").mock(
            return_value=Response(200, json={
                "id": 1,
                "title": "Test",
                "articleCount": 2,
            })
        )
        respx_mock.get("http://test-zammad.local/api/v1/ticket_articles/by_ticket/1").mock(
            return_value=Response(200, json={
                "ticket_articles": [
                    {"id": 1, "ticketId": 1, "body": "Article 1"},
                    {"id": 2, "ticketId": 1, "body": "Article 2"},
                ]
            })
        )

        client = ZammadClient()
        ticket = client.get_ticket(1, include_articles=True)

        assert ticket.articles is not None
        assert len(ticket.articles) == 2

    def test_search_tickets(self, zammad_api_mock: Any) -> None:
        """Test searching tickets."""
        client = ZammadClient()
        result = client.search_tickets(query="test", state="open")

        assert result.total_count > 0
        assert len(result.items) > 0

    def test_create_ticket(self, zammad_api_mock: Any) -> None:
        """Test creating a ticket."""
        client = ZammadClient()
        request = TicketCreateRequest(
            title="New Ticket",
            group="Support",
            customer="test@example.com",
            article_body="Test content",
        )

        ticket = client.create_ticket(request)
        assert ticket.id is not None
        assert ticket.title == "New Ticket"

    def test_update_ticket(self, zammad_api_mock: Any) -> None:
        """Test updating a ticket."""
        client = ZammadClient()

        from zammad_mcp_server.models import TicketUpdateRequest
        request = TicketUpdateRequest(title="Updated Title")

        ticket = client.update_ticket(1, request)
        assert ticket.title == "Updated Title"

    def test_delete_ticket(self, respx_mock: respx.MockRouter) -> None:
        """Test deleting a ticket."""
        respx_mock.delete("http://test-zammad.local/api/v1/tickets/1").mock(
            return_value=Response(200)
        )

        client = ZammadClient()
        result = client.delete_ticket(1)
        assert result is True

    def test_get_ticket_articles(self, zammad_api_mock: Any) -> None:
        """Test getting ticket articles."""
        client = ZammadClient()
        articles = client.get_ticket_articles(1)

        assert len(articles) > 0

    def test_create_article(self, zammad_api_mock: Any) -> None:
        """Test creating an article."""
        client = ZammadClient()
        request = ArticleCreateRequest(
            ticket_id=1,
            body="New article content",
            internal=False,
        )

        article = client.create_article(request)
        assert article.id is not None
        assert article.body == "New article content"

    def test_get_user(self, zammad_api_mock: Any) -> None:
        """Test getting a user."""
        client = ZammadClient()
        user = client.get_user(1)

        assert user.id == 1
        assert user.email is not None

    def test_search_users(self, zammad_api_mock: Any) -> None:
        """Test searching users."""
        client = ZammadClient()
        result = client.search_users(query="test")

        assert result.total_count > 0

    def test_create_user(self, zammad_api_mock: Any) -> None:
        """Test creating a user."""
        client = ZammadClient()
        request = UserCreateRequest(
            email="new@example.com",
            firstname="New",
            lastname="User",
        )

        user = client.create_user(request)
        assert user.id is not None
        assert user.email == "new@example.com"

    def test_get_organization(self, zammad_api_mock: Any) -> None:
        """Test getting an organization."""
        client = ZammadClient()
        org = client.get_organization(1)

        assert org.id == 1
        assert org.name is not None

    def test_search_organizations(self, zammad_api_mock: Any) -> None:
        """Test searching organizations."""
        client = ZammadClient()
        result = client.search_organizations(query="test")

        assert result.total_count > 0

    def test_create_organization(self, zammad_api_mock: Any) -> None:
        """Test creating an organization."""
        client = ZammadClient()
        request = OrganizationCreateRequest(name="New Org")

        org = client.create_organization(request)
        assert org.id is not None
        assert org.name == "New Org"

    def test_list_groups(self, zammad_api_mock: Any) -> None:
        """Test listing groups."""
        client = ZammadClient()
        groups = client.list_groups()

        assert len(groups) > 0

    def test_get_ticket_states(self, zammad_api_mock: Any) -> None:
        """Test getting ticket states."""
        client = ZammadClient()
        states = client.get_ticket_states()

        assert len(states) > 0

    def test_get_priorities(self, zammad_api_mock: Any) -> None:
        """Test getting priorities."""
        client = ZammadClient()
        priorities = client.get_priorities()

        assert len(priorities) > 0

    def test_caching(self, respx_mock: respx.MockRouter) -> None:
        """Test that caching works."""
        respx_mock.get("http://test-zammad.local/api/v1/groups").mock(
            return_value=Response(200, json=[{"id": 1, "name": "Support"}])
        )

        client = ZammadClient()

        # First call should hit the API
        groups1 = client.list_groups()
        assert len(groups1) == 1

        # Second call should use cache
        groups2 = client.list_groups()
        assert len(groups2) == 1

        # Clear cache
        client.clear_caches()


class TestZammadClientErrors:
    """Test suite for error handling."""

    def test_authentication_error(self, respx_mock: respx.MockRouter) -> None:
        """Test handling of 401 authentication error."""
        respx_mock.get("http://test-zammad.local/api/v1/ping").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        client = ZammadClient()
        with pytest.raises(AuthenticationError):
            client.health_check()

    def test_not_found_error(self, respx_mock: respx.MockRouter) -> None:
        """Test handling of 404 not found error."""
        respx_mock.get("http://test-zammad.local/api/v1/tickets/999").mock(
            return_value=Response(404)
        )

        client = ZammadClient()
        with pytest.raises(NotFoundError):
            client.get_ticket(999)

    def test_server_error(self, respx_mock: respx.MockRouter) -> None:
        """Test handling of 500 server error."""
        respx_mock.get("http://test-zammad.local/api/v1/ping").mock(
            return_value=Response(500, text="Internal Server Error")
        )

        client = ZammadClient()
        with pytest.raises(ZammadClientError):
            client.health_check()

    def test_network_error(self, respx_mock: respx.MockRouter) -> None:
        """Test handling of network errors."""
        respx_mock.get("http://test-zammad.local/api/v1/ping").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        client = ZammadClient()
        result = client.health_check()
        assert result["status"] == "unhealthy"


class TestClientContextManager:
    """Test suite for context manager usage."""

    def test_context_manager(self) -> None:
        """Test using client as context manager."""
        with ZammadClient() as client:
            assert client._client is not None

        # After exiting context, client should be closed
        assert client._client is None

    def test_explicit_close(self) -> None:
        """Test explicit close method."""
        client = ZammadClient()
        assert client._client is not None

        client.close()
        assert client._client is None
