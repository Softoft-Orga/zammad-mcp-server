"""Tests for Zammad MCP Server access control."""

import os
from typing import Any

import pytest

from zammad_mcp_server.access_control import (
    AccessController,
    AccessPolicy,
    Permission,
    ToolCategory,
    TOOL_CATEGORIES,
)


class TestAccessPolicy:
    """Test suite for AccessPolicy."""

    def test_default_policy(self) -> None:
        """Test default policy creation."""
        policy = AccessPolicy()
        assert policy.default_permission == Permission.READ_ONLY
        assert policy.allowed_groups is None

    def test_policy_with_all_category(self) -> None:
        """Test that ALL category populates other categories."""
        policy = AccessPolicy(
            category_permissions={
                ToolCategory.ALL: Permission.WRITE,
            }
        )
        # Check that ALL permission was applied to other categories
        assert policy.category_permissions[ToolCategory.TICKETS] == Permission.WRITE
        assert policy.category_permissions[ToolCategory.USERS] == Permission.WRITE

    def test_policy_with_specific_categories(self) -> None:
        """Test policy with specific category permissions."""
        policy = AccessPolicy(
            category_permissions={
                ToolCategory.TICKETS: Permission.WRITE,
                ToolCategory.USERS: Permission.READ_ONLY,
                ToolCategory.ADMIN: Permission.DENIED,
            }
        )
        assert policy.category_permissions[ToolCategory.TICKETS] == Permission.WRITE
        assert policy.category_permissions[ToolCategory.USERS] == Permission.READ_ONLY
        assert policy.category_permissions[ToolCategory.ADMIN] == Permission.DENIED

    def test_policy_with_denied_tools(self) -> None:
        """Test policy with explicitly denied tools."""
        policy = AccessPolicy(
            denied_tools={"delete_ticket", "delete_user"},
        )
        assert "delete_ticket" in policy.denied_tools
        assert "delete_user" in policy.denied_tools

    def test_policy_with_group_restrictions(self) -> None:
        """Test policy with group restrictions."""
        policy = AccessPolicy(
            allowed_groups={"Support", "Sales"},
        )
        assert policy.allowed_groups == {"Support", "Sales"}


class TestAccessController:
    """Test suite for AccessController."""

    def test_can_execute_allowed(self) -> None:
        """Test that allowed tools can execute."""
        policy = AccessPolicy(default_permission=Permission.WRITE)
        controller = AccessController(policy)

        assert controller.can_execute("get_ticket") is True
        assert controller.can_execute("create_ticket") is True

    def test_can_execute_denied(self) -> None:
        """Test that denied tools cannot execute."""
        policy = AccessPolicy(
            default_permission=Permission.WRITE,
            denied_tools={"delete_ticket"},
        )
        controller = AccessController(policy)

        assert controller.can_execute("get_ticket") is True
        assert controller.can_execute("delete_ticket") is False

    def test_can_execute_by_category_denied(self) -> None:
        """Test that tools in denied categories cannot execute."""
        policy = AccessPolicy(
            category_permissions={
                ToolCategory.TICKETS: Permission.DENIED,
            }
        )
        controller = AccessController(policy)

        assert controller.can_execute("get_ticket") is False
        assert controller.can_execute("create_ticket") is False

    def test_can_read_readonly(self) -> None:
        """Test read permission checking."""
        policy = AccessPolicy(default_permission=Permission.READ_ONLY)
        controller = AccessController(policy)

        assert controller.can_read("get_ticket") is True
        assert controller.can_write("get_ticket") is False

    def test_can_write_with_write_permission(self) -> None:
        """Test write permission checking."""
        policy = AccessPolicy(
            category_permissions={
                ToolCategory.TICKETS: Permission.WRITE,
            }
        )
        controller = AccessController(policy)

        assert controller.can_write("create_ticket") is True
        assert controller.can_write("update_ticket") is True

    def test_can_admin_only_admin(self) -> None:
        """Test admin permission checking."""
        policy = AccessPolicy(
            category_permissions={
                ToolCategory.TICKETS: Permission.ADMIN,
            }
        )
        controller = AccessController(policy)

        assert controller.can_admin("delete_ticket") is True
        assert controller.can_write("delete_ticket") is False
        assert controller.can_read("delete_ticket") is False

    def test_tool_permission_overrides_category(self) -> None:
        """Test that specific tool permissions override category."""
        policy = AccessPolicy(
            category_permissions={
                ToolCategory.TICKETS: Permission.READ_ONLY,
            },
            tool_permissions={
                "create_ticket": Permission.WRITE,
            },
        )
        controller = AccessController(policy)

        assert controller.can_read("get_ticket") is True
        assert controller.can_write("get_ticket") is False
        assert controller.can_write("create_ticket") is True

    def test_wildcard_denied_tools(self) -> None:
        """Test wildcard patterns in denied tools."""
        policy = AccessPolicy(
            default_permission=Permission.WRITE,
            denied_tools={"delete_*"},
        )
        controller = AccessController(policy)

        assert controller.can_execute("delete_ticket") is False
        assert controller.can_execute("delete_user") is False
        assert controller.can_execute("get_ticket") is True

    def test_filter_ticket_allowed_group(self) -> None:
        """Test ticket filtering with allowed group."""
        policy = AccessPolicy(
            allowed_groups={"Support"},
        )
        controller = AccessController(policy)

        ticket = {"id": 1, "group": {"name": "Support"}}
        assert controller.filter_ticket(ticket) == ticket

    def test_filter_ticket_denied_group(self) -> None:
        """Test ticket filtering with denied group."""
        policy = AccessPolicy(
            allowed_groups={"Support"},
        )
        controller = AccessController(policy)

        ticket = {"id": 1, "group": {"name": "Admin"}}
        assert controller.filter_ticket(ticket) is None

    def test_filter_ticket_no_restrictions(self) -> None:
        """Test ticket filtering without group restrictions."""
        policy = AccessPolicy()
        controller = AccessController(policy)

        ticket = {"id": 1, "group": {"name": "AnyGroup"}}
        assert controller.filter_ticket(ticket) == ticket

    def test_filter_ticket_string_group(self) -> None:
        """Test ticket filtering when group is a string."""
        policy = AccessPolicy(
            allowed_groups={"Support"},
        )
        controller = AccessController(policy)

        ticket = {"id": 1, "group": "Support"}
        assert controller.filter_ticket(ticket) == ticket

        ticket2 = {"id": 2, "group": "Admin"}
        assert controller.filter_ticket(ticket2) is None

    def test_access_logging(self) -> None:
        """Test that access is logged."""
        policy = AccessPolicy()
        controller = AccessController(policy)

        controller.log_access("get_ticket", True)
        controller.log_access("delete_ticket", False, client_info={"ip": "127.0.0.1"})

        log = controller.get_access_log()
        assert len(log) == 2
        assert log[0]["tool"] == "get_ticket"
        assert log[0]["allowed"] is True
        assert log[1]["tool"] == "delete_ticket"
        assert log[1]["allowed"] is False

    def test_get_allowed_tools(self) -> None:
        """Test getting list of allowed tools."""
        policy = AccessPolicy(
            default_permission=Permission.READ_ONLY,
            denied_tools={"delete_ticket", "delete_user"},
        )
        controller = AccessController(policy)

        allowed = controller.get_allowed_tools()
        assert "delete_ticket" not in allowed
        assert "delete_user" not in allowed
        assert "get_ticket" in allowed
        assert "search_tickets" in allowed

    def test_get_tool_info(self) -> None:
        """Test getting detailed tool information."""
        policy = AccessPolicy(
            default_permission=Permission.READ_ONLY,
            category_permissions={
                ToolCategory.ADMIN: Permission.DENIED,
            },
        )
        controller = AccessController(policy)

        info = controller.get_tool_info()
        ticket_info = next(i for i in info if i["tool"] == "get_ticket")
        admin_info = next(i for i in info if i["tool"] == "get_ticket_states")

        assert ticket_info["accessible"] == "True"
        assert ticket_info["category"] == "tickets"
        assert admin_info["accessible"] == "False"


class TestAccessControllerFromEnv:
    """Test suite for AccessController.from_env factory method."""

    def test_from_env_all_categories(self, monkeypatch: Any) -> None:
        """Test creating controller with all categories allowed."""
        monkeypatch.setenv("MCP_ALLOWED_CATEGORIES", "all")
        monkeypatch.setenv("MCP_DENIED_TOOLS", "delete_ticket")

        controller = AccessController.from_env()

        assert controller.can_write("create_ticket") is True
        assert controller.can_execute("delete_ticket") is False

    def test_from_env_specific_categories(self, monkeypatch: Any) -> None:
        """Test creating controller with specific categories."""
        monkeypatch.setenv("MCP_ALLOWED_CATEGORIES", "tickets,groups")
        monkeypatch.delenv("MCP_DENIED_TOOLS", raising=False)

        controller = AccessController.from_env()

        assert controller.can_read("get_ticket") is True
        assert controller.can_write("create_ticket") is True
        assert controller.can_execute("get_user") is False
        assert controller.can_execute("create_user") is False

    def test_from_env_with_groups(self, monkeypatch: Any) -> None:
        """Test creating controller with group restrictions."""
        monkeypatch.setenv("MCP_ALLOWED_CATEGORIES", "all")
        monkeypatch.setenv("MCP_ALLOWED_GROUPS", "Support,Sales")
        monkeypatch.delenv("MCP_DENIED_TOOLS", raising=False)

        controller = AccessController.from_env()

        assert controller.policy.allowed_groups == {"Support", "Sales"}

        ticket_allowed = {"id": 1, "group": "Support"}
        ticket_denied = {"id": 2, "group": "Admin"}

        assert controller.filter_ticket(ticket_allowed) == ticket_allowed
        assert controller.filter_ticket(ticket_denied) is None
