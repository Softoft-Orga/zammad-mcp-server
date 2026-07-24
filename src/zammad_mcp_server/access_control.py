"""Access control and permission management for Zammad MCP Server."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import structlog

logger = structlog.get_logger()


class Permission(Enum):
    """Permission levels for MCP tools."""

    DENIED = auto()
    READ_ONLY = auto()
    WRITE = auto()
    ADMIN = auto()


class ToolCategory(Enum):
    """Categories of MCP tools for access control."""

    TICKETS = "tickets"
    USERS = "users"
    ORGANIZATIONS = "organizations"
    GROUPS = "groups"
    SEARCH = "search"
    ADMIN = "admin"
    SYSTEM = "system"
    ALL = "all"


# Mapping of tools to their categories
TOOL_CATEGORIES: dict[str, ToolCategory] = {
    # Ticket tools
    "get_ticket": ToolCategory.TICKETS,
    "search_tickets": ToolCategory.TICKETS,
    "create_ticket": ToolCategory.TICKETS,
    "update_ticket": ToolCategory.TICKETS,
    "delete_ticket": ToolCategory.TICKETS,
    "get_ticket_articles": ToolCategory.TICKETS,
    "create_article": ToolCategory.TICKETS,
    "create_time_accounting": ToolCategory.TICKETS,
    "get_time_accountings": ToolCategory.TICKETS,
    "get_ticket_stats": ToolCategory.TICKETS,
    "merge_tickets": ToolCategory.TICKETS,
    "link_tickets": ToolCategory.TICKETS,
    # User tools
    "get_user": ToolCategory.USERS,
    "search_users": ToolCategory.USERS,
    "create_user": ToolCategory.USERS,
    "update_user": ToolCategory.USERS,
    "delete_user": ToolCategory.USERS,
    "get_current_user": ToolCategory.USERS,
    # Organization tools
    "get_organization": ToolCategory.ORGANIZATIONS,
    "search_organizations": ToolCategory.ORGANIZATIONS,
    "create_organization": ToolCategory.ORGANIZATIONS,
    "update_organization": ToolCategory.ORGANIZATIONS,
    "delete_organization": ToolCategory.ORGANIZATIONS,
    # Group tools
    "get_group": ToolCategory.GROUPS,
    "list_groups": ToolCategory.GROUPS,
    "create_group": ToolCategory.GROUPS,
    # Search tools
    "search": ToolCategory.SEARCH,
    "full_text_search": ToolCategory.SEARCH,
    # Admin tools
    "get_ticket_states": ToolCategory.ADMIN,
    "get_priorities": ToolCategory.ADMIN,
    "get_tags": ToolCategory.ADMIN,
    # System tools
    "health_check": ToolCategory.SYSTEM,
    "get_server_info": ToolCategory.SYSTEM,
}


@dataclass
class AccessPolicy:
    """Access policy configuration."""

    # Default permission for all tools
    default_permission: Permission = Permission.READ_ONLY

    # Category permissions
    category_permissions: dict[ToolCategory, Permission] = field(default_factory=dict)

    # Specific tool permissions (overrides category)
    tool_permissions: dict[str, Permission] = field(default_factory=dict)

    # Denied tools (takes precedence)
    denied_tools: set[str] = field(default_factory=set)

    # Allowed ticket scopes (for read filtering)
    allowed_groups: set[str] | None = None
    allowed_organizations: set[int] | None = None

    # Rate limiting
    rate_limit_per_minute: int = 60

    def __post_init__(self) -> None:
        """Validate and normalize the policy."""
        # Ensure ALL category covers everything if set
        if ToolCategory.ALL in self.category_permissions:
            all_perm = self.category_permissions[ToolCategory.ALL]
            for cat in ToolCategory:
                if cat != ToolCategory.ALL and cat not in self.category_permissions:
                    self.category_permissions[cat] = all_perm


class AccessController:
    """Controller for managing access permissions to MCP tools."""

    def __init__(self, policy: AccessPolicy | None = None) -> None:
        """Initialize with an access policy."""
        self.policy = policy or AccessPolicy()
        self._access_log: list[dict[str, Any]] = []

    def can_execute(self, tool_name: str) -> bool:
        """Check if a tool can be executed."""
        # Check explicitly denied tools first
        if self._is_denied(tool_name):
            return False

        # Get permission level
        permission = self._get_permission(tool_name)
        return permission != Permission.DENIED

    def can_read(self, tool_name: str) -> bool:
        """Check if read operations are allowed."""
        permission = self._get_permission(tool_name)
        return permission in (Permission.READ_ONLY, Permission.WRITE, Permission.ADMIN)

    def can_write(self, tool_name: str) -> bool:
        """Check if write operations are allowed."""
        permission = self._get_permission(tool_name)
        return permission in (Permission.WRITE, Permission.ADMIN)

    def can_admin(self, tool_name: str) -> bool:
        """Check if admin operations are allowed."""
        permission = self._get_permission(tool_name)
        return permission == Permission.ADMIN

    def _is_denied(self, tool_name: str) -> bool:
        """Check if tool is explicitly denied."""
        # Exact match
        if tool_name in self.policy.denied_tools:
            return True

        # Pattern match
        for pattern in self.policy.denied_tools:
            if fnmatch.fnmatch(tool_name, pattern):
                return True

        return False

    def _get_permission(self, tool_name: str) -> Permission:
        """Get the permission level for a tool."""
        # Check explicit tool permission first
        if tool_name in self.policy.tool_permissions:
            return self.policy.tool_permissions[tool_name]

        # Check category permission
        category = TOOL_CATEGORIES.get(tool_name, ToolCategory.ALL)
        if category in self.policy.category_permissions:
            return self.policy.category_permissions[category]

        # Fall back to default
        return self.policy.default_permission

    def filter_ticket(self, ticket: dict[str, Any]) -> dict[str, Any] | None:
        """Filter ticket data based on policy restrictions."""
        # Check group restrictions
        if self.policy.allowed_groups is not None:
            group = ticket.get("group", "")
            if isinstance(group, dict):
                group = group.get("name", "")
            if group not in self.policy.allowed_groups:
                return None

        # Check organization restrictions
        if self.policy.allowed_organizations is not None:
            org_id = ticket.get("organization_id")
            if org_id is not None and org_id not in self.policy.allowed_organizations:
                return None

        return ticket

    def log_access(
        self,
        tool_name: str,
        allowed: bool,
        client_info: dict[str, Any] | None = None,
    ) -> None:
        """Log an access attempt."""
        import time

        entry = {
            "timestamp": time.time(),
            "tool": tool_name,
            "allowed": allowed,
            "permission": self._get_permission(tool_name).name,
            "client": client_info or {},
        }
        self._access_log.append(entry)

        if not allowed:
            logger.warning(
                "access_denied",
                tool=tool_name,
                client=client_info,
            )

    def get_access_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent access log entries."""
        return self._access_log[-limit:]

    @classmethod
    def from_env(cls) -> AccessController:
        """Create an access controller from environment variables."""
        import os

        # Parse allowed categories
        allowed_categories_str = os.getenv("MCP_ALLOWED_CATEGORIES", "all")
        allowed_categories = {cat.strip().lower() for cat in allowed_categories_str.split(",")}

        # Build category permissions
        category_permissions: dict[ToolCategory, Permission] = {}

        if "all" in allowed_categories:
            category_permissions[ToolCategory.ALL] = Permission.WRITE
        else:
            for cat in ToolCategory:
                if cat.value in allowed_categories:
                    category_permissions[cat] = Permission.WRITE
                else:
                    category_permissions[cat] = Permission.DENIED

        # Parse denied tools
        denied_tools_str = os.getenv("MCP_DENIED_TOOLS", "")
        denied_tools = {tool.strip() for tool in denied_tools_str.split(",") if tool.strip()}

        # Parse allowed groups
        allowed_groups_str = os.getenv("MCP_ALLOWED_GROUPS", "")
        allowed_groups = None
        if allowed_groups_str:
            allowed_groups = {g.strip() for g in allowed_groups_str.split(",")}

        policy = AccessPolicy(
            default_permission=Permission.READ_ONLY,
            category_permissions=category_permissions,
            denied_tools=denied_tools,
            allowed_groups=allowed_groups,
        )

        return cls(policy)

    def get_allowed_tools(self) -> list[str]:
        """Get list of all allowed tools based on current policy."""
        allowed = []
        for tool_name in TOOL_CATEGORIES:
            if self.can_execute(tool_name):
                allowed.append(tool_name)
        return sorted(allowed)

    def get_tool_info(self) -> list[dict[str, str]]:
        """Get detailed information about all tools and their permissions."""
        info = []
        for tool_name, category in sorted(TOOL_CATEGORIES.items()):
            permission = self._get_permission(tool_name)
            is_denied = self._is_denied(tool_name)
            info.append({
                "tool": tool_name,
                "category": category.value,
                "permission": permission.name,
                "accessible": str(not is_denied and permission != Permission.DENIED),
            })
        return info
