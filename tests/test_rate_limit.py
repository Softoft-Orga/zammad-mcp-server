"""Rate-limit tests for AccessController."""

import pytest

from zammad_mcp_server.access_control import (
    AccessController,
    AccessPolicy,
    Permission,
    ToolCategory,
)


def test_rate_limit_blocks_after_budget() -> None:
    controller = AccessController(
        AccessPolicy(
            default_permission=Permission.WRITE,
            category_permissions={ToolCategory.ALL: Permission.WRITE},
            rate_limit_per_minute=2,
        )
    )
    controller.consume_rate_limit()
    controller.consume_rate_limit()
    with pytest.raises(PermissionError, match="Rate limit"):
        controller.consume_rate_limit()


def test_rate_limit_disabled_when_zero() -> None:
    controller = AccessController(
        AccessPolicy(
            default_permission=Permission.WRITE,
            category_permissions={ToolCategory.ALL: Permission.WRITE},
            rate_limit_per_minute=0,
        )
    )
    for _ in range(20):
        controller.consume_rate_limit()
