"""Tests for Zammad MCP Server tools and server functionality."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestHealthCheckTool:
    """Test suite for health_check tool."""

    def test_health_check_success(self, unrestricted_controller: Any) -> None:
        """Test health check with working connection."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_client.health_check.return_value = {"status": "healthy", "response": {"version": "6.0"}}
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import health_check
            result = health_check()

            assert result["mcp_server"] == "healthy"
            assert result["zammad_connection"]["status"] == "healthy"

    def test_health_check_access_denied(self, restricted_controller: Any) -> None:
        """Test health check with read-only access."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = restricted_controller

            from zammad_mcp_server.server import health_check
            # health_check should work with read-only access
            result = health_check()
            assert result["mcp_server"] == "healthy"


class TestTicketTools:
    """Test suite for ticket-related tools."""

    def test_get_ticket_success(self, unrestricted_controller: Any) -> None:
        """Test getting a ticket successfully."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_ticket = MagicMock()
            mock_ticket.model_dump.return_value = {
                "id": 1,
                "title": "Test Ticket",
                "group": "Support",
            }
            mock_client.get_ticket.return_value = mock_ticket
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_ticket
            result = get_ticket(1)

            assert result["id"] == 1
            assert result["title"] == "Test Ticket"

    def test_get_ticket_not_found(self, unrestricted_controller: Any) -> None:
        """Test getting a non-existent ticket."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            from zammad_mcp_server.client import NotFoundError
            mock_client.get_ticket.side_effect = NotFoundError("Not found", 404)
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_ticket
            result = get_ticket(999)

            assert "error" in result
            assert "999" in result["error"]

    def test_get_ticket_access_denied(self, restricted_controller: Any) -> None:
        """Test getting a ticket with restricted access."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_ticket = MagicMock()
            mock_ticket.model_dump.return_value = {
                "id": 1,
                "title": "Test",
                "group": {"name": "Admin"},  # Restricted group
            }
            mock_client.get_ticket.return_value = mock_ticket
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = restricted_controller

            from zammad_mcp_server.server import get_ticket
            result = get_ticket(1)

            assert "error" in result
            assert "Access denied" in result["error"]

    def test_search_tickets(self, unrestricted_controller: Any) -> None:
        """Test searching tickets."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.items = [
                MagicMock(model_dump=lambda: {"id": 1, "title": "Ticket 1"}),
                MagicMock(model_dump=lambda: {"id": 2, "title": "Ticket 2"}),
            ]
            mock_result.total_count = 2
            mock_client.search_tickets.return_value = mock_result
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import search_tickets
            result = search_tickets(query="test")

            assert len(result["tickets"]) == 2
            assert result["total_count"] == 2

    def test_create_ticket(self, unrestricted_controller: Any) -> None:
        """Test creating a ticket."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_ticket = MagicMock()
            mock_ticket.model_dump.return_value = {
                "id": 999,
                "title": "New Ticket",
                "group": "Support",
            }
            mock_client.create_ticket.return_value = mock_ticket
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import create_ticket
            result = create_ticket(
                title="New Ticket",
                group="Support",
                customer="test@example.com",
            )

            assert result["id"] == 999
            assert result["title"] == "New Ticket"

    def test_create_ticket_access_denied(self, read_only_controller: Any) -> None:
        """Test creating a ticket with read-only access."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_get_client.return_value = MagicMock()
            mock_get_controller.return_value = read_only_controller

            from zammad_mcp_server.server import create_ticket
            with pytest.raises(PermissionError):
                create_ticket(title="New", group="Support")

    def test_update_ticket(self, unrestricted_controller: Any) -> None:
        """Test updating a ticket."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_ticket = MagicMock()
            mock_ticket.model_dump.return_value = {
                "id": 1,
                "title": "Updated Title",
            }
            mock_client.update_ticket.return_value = mock_ticket
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import update_ticket
            result = update_ticket(ticket_id=1, title="Updated Title")

            assert result["title"] == "Updated Title"

    def test_delete_ticket(self, unrestricted_controller: Any) -> None:
        """Test deleting a ticket."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_client.delete_ticket.return_value = True
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import delete_ticket
            result = delete_ticket(1)

            assert result["success"] is True

    def test_delete_ticket_access_denied(self, restricted_controller: Any) -> None:
        """Test deleting a ticket with restricted access."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_get_client.return_value = MagicMock()
            mock_get_controller.return_value = restricted_controller

            from zammad_mcp_server.server import delete_ticket
            with pytest.raises(PermissionError):
                delete_ticket(1)

    def test_get_ticket_articles(self, unrestricted_controller: Any) -> None:
        """Test getting ticket articles."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_article = MagicMock()
            mock_article.model_dump.return_value = {"id": 1, "body": "Test"}
            mock_client.get_ticket_articles.return_value = [mock_article]
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_ticket_articles
            result = get_ticket_articles(1)

            assert result["ticket_id"] == 1
            assert len(result["articles"]) == 1

    def test_create_article(self, unrestricted_controller: Any) -> None:
        """Test creating an article."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_article = MagicMock()
            mock_article.model_dump.return_value = {"id": 1, "body": "New content"}
            mock_client.create_article.return_value = mock_article
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import create_article
            result = create_article(ticket_id=1, body="New content")

            assert result["body"] == "New content"

    def test_get_ticket_stats(self, unrestricted_controller: Any) -> None:
        """Test getting ticket statistics."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_stats = MagicMock()
            mock_stats.model_dump.return_value = {
                "total": 100,
                "open": 20,
                "closed": 70,
            }
            mock_client.get_ticket_stats.return_value = mock_stats
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_ticket_stats
            result = get_ticket_stats()

            assert result["total"] == 100
            assert result["open"] == 20

    def test_get_ticket_states(self, unrestricted_controller: Any) -> None:
        """Test getting ticket states."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_client.get_ticket_states.return_value = [
                {"id": 1, "name": "new"},
                {"id": 2, "name": "open"},
            ]
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_ticket_states
            result = get_ticket_states()

            assert len(result) == 2


class TestUserTools:
    """Test suite for user-related tools."""

    def test_get_user(self, unrestricted_controller: Any) -> None:
        """Test getting a user."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_user = MagicMock()
            mock_user.model_dump.return_value = {"id": 1, "email": "test@example.com"}
            mock_client.get_user.return_value = mock_user
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_user
            result = get_user(1)

            assert result["id"] == 1

    def test_search_users(self, unrestricted_controller: Any) -> None:
        """Test searching users."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.items = [
                MagicMock(model_dump=lambda: {"id": 1, "email": "user1@example.com"}),
            ]
            mock_result.total_count = 1
            mock_client.search_users.return_value = mock_result
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import search_users
            result = search_users(query="test")

            assert len(result["users"]) == 1

    def test_create_user(self, unrestricted_controller: Any) -> None:
        """Test creating a user."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_user = MagicMock()
            mock_user.model_dump.return_value = {"id": 1, "email": "new@example.com"}
            mock_client.create_user.return_value = mock_user
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import create_user
            result = create_user(email="new@example.com", firstname="New", lastname="User")

            assert result["email"] == "new@example.com"

    def test_update_user(self, unrestricted_controller: Any) -> None:
        """Test updating a user."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_user = MagicMock()
            mock_user.model_dump.return_value = {"id": 1, "firstname": "Updated"}
            mock_client.update_user.return_value = mock_user
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import update_user
            result = update_user(user_id=1, firstname="Updated")

            assert result["firstname"] == "Updated"

    def test_delete_user(self, unrestricted_controller: Any) -> None:
        """Test deleting a user."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_client.delete_user.return_value = True
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import delete_user
            result = delete_user(1)

            assert result["success"] is True

    def test_get_current_user(self, unrestricted_controller: Any) -> None:
        """Test getting current user."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_user = MagicMock()
            mock_user.model_dump.return_value = {"id": 1, "email": "me@example.com"}
            mock_client.get_current_user.return_value = mock_user
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_current_user
            result = get_current_user()

            assert result["email"] == "me@example.com"


class TestOrganizationTools:
    """Test suite for organization-related tools."""

    def test_get_organization(self, unrestricted_controller: Any) -> None:
        """Test getting an organization."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_org = MagicMock()
            mock_org.model_dump.return_value = {"id": 1, "name": "Test Org"}
            mock_client.get_organization.return_value = mock_org
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_organization
            result = get_organization(1)

            assert result["name"] == "Test Org"

    def test_search_organizations(self, unrestricted_controller: Any) -> None:
        """Test searching organizations."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.items = [
                MagicMock(model_dump=lambda: {"id": 1, "name": "Org 1"}),
            ]
            mock_result.total_count = 1
            mock_client.search_organizations.return_value = mock_result
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import search_organizations
            result = search_organizations(query="test")

            assert len(result["organizations"]) == 1

    def test_create_organization(self, unrestricted_controller: Any) -> None:
        """Test creating an organization."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_org = MagicMock()
            mock_org.model_dump.return_value = {"id": 1, "name": "New Org"}
            mock_client.create_organization.return_value = mock_org
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import create_organization
            result = create_organization(name="New Org")

            assert result["name"] == "New Org"


class TestGroupTools:
    """Test suite for group-related tools."""

    def test_get_group(self, unrestricted_controller: Any) -> None:
        """Test getting a group."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_group = MagicMock()
            mock_group.model_dump.return_value = {"id": 1, "name": "Support"}
            mock_client.get_group.return_value = mock_group
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_group
            result = get_group(1)

            assert result["name"] == "Support"

    def test_list_groups(self, unrestricted_controller: Any) -> None:
        """Test listing groups."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_group = MagicMock()
            mock_group.model_dump.return_value = {"id": 1, "name": "Support"}
            mock_client.list_groups.return_value = [mock_group]
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import list_groups
            result = list_groups()

            assert len(result["groups"]) == 1
            assert result["count"] == 1


class TestToolInfo:
    """Test suite for tool information."""

    def test_get_allowed_tools(self, unrestricted_controller: Any) -> None:
        """Test getting allowed tools information."""
        with patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:
            mock_get_controller.return_value = unrestricted_controller

            from zammad_mcp_server.server import get_allowed_tools
            result = get_allowed_tools()

            assert isinstance(result, list)
            assert len(result) > 0


class TestAccessControlIntegration:
    """Test suite for access control integration."""

    def test_read_only_cannot_create_ticket(self, read_only_controller: Any) -> None:
        """Test that read-only policy prevents ticket creation."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_get_client.return_value = MagicMock()
            mock_get_controller.return_value = read_only_controller

            from zammad_mcp_server.server import create_ticket
            with pytest.raises(PermissionError):
                create_ticket(title="Test", group="Support")

    def test_read_only_cannot_update_ticket(self, read_only_controller: Any) -> None:
        """Test that read-only policy prevents ticket updates."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_get_client.return_value = MagicMock()
            mock_get_controller.return_value = read_only_controller

            from zammad_mcp_server.server import update_ticket
            with pytest.raises(PermissionError):
                update_ticket(ticket_id=1, title="New Title")

    def test_read_only_cannot_create_article(self, read_only_controller: Any) -> None:
        """Test that read-only policy prevents article creation."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_get_client.return_value = MagicMock()
            mock_get_controller.return_value = read_only_controller

            from zammad_mcp_server.server import create_article
            with pytest.raises(PermissionError):
                create_article(ticket_id=1, body="New content")

    def test_read_only_can_search(self, read_only_controller: Any) -> None:
        """Test that read-only policy allows searching."""
        with patch("zammad_mcp_server.server.get_client") as mock_get_client, \
             patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller:

            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.items = []
            mock_result.total_count = 0
            mock_client.search_tickets.return_value = mock_result
            mock_get_client.return_value = mock_client
            mock_get_controller.return_value = read_only_controller

            from zammad_mcp_server.server import search_tickets
            result = search_tickets()

            assert "tickets" in result
