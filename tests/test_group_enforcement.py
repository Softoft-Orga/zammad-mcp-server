"""Tests for group write enforcement."""

from unittest.mock import MagicMock, patch

import pytest

from zammad_mcp_server.access_control import (
    AccessController,
    AccessPolicy,
    Permission,
    ToolCategory,
)


def _controller() -> AccessController:
    return AccessController(
        AccessPolicy(
            default_permission=Permission.WRITE,
            category_permissions={ToolCategory.ALL: Permission.WRITE},
            allowed_groups={"Support"},
            rate_limit_per_minute=0,
        )
    )


def test_create_ticket_blocks_other_group() -> None:
    with (
        patch("zammad_mcp_server.server.get_client") as mock_get_client,
        patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller,
    ):
        mock_get_client.return_value = MagicMock()
        mock_get_controller.return_value = _controller()
        from zammad_mcp_server.server import create_ticket

        with pytest.raises(PermissionError, match="group"):
            create_ticket(title="Nope", group="Sales")


def test_assert_group_allowed_passes_support() -> None:
    controller = _controller()
    controller.assert_group_allowed("Support")


def test_assert_group_allowed_rejects_sales() -> None:
    controller = _controller()
    with pytest.raises(PermissionError):
        controller.assert_group_allowed("Sales")
