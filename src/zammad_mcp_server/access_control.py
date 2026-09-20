"""Access control and permission management for Zammad MCP Server."""

from __future__ import annotations

import fnmatch
import json
import os
import time
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


# Single source of truth: every @mcp.tool() name must appear here.
TOOL_CATEGORIES: dict[str, ToolCategory] = {
    "get_ticket": ToolCategory.TICKETS,
    "search_tickets": ToolCategory.TICKETS,
    "create_ticket": ToolCategory.TICKETS,
    "update_ticket": ToolCategory.TICKETS,
    "delete_ticket": ToolCategory.TICKETS,
    "get_ticket_articles": ToolCategory.TICKETS,
    "create_article": ToolCategory.TICKETS,
    "get_ticket_stats": ToolCategory.TICKETS,
    "merge_tickets": ToolCategory.TICKETS,
    "link_tickets": ToolCategory.TICKETS,
    "summarize_ticket": ToolCategory.TICKETS,
    "list_ticket_tags": ToolCategory.TICKETS,
    "add_ticket_tag": ToolCategory.TICKETS,
    "remove_ticket_tag": ToolCategory.TICKETS,
    "get_article_attachment": ToolCategory.TICKETS,
    "get_user": ToolCategory.USERS,
    "search_users": ToolCategory.USERS,
    "create_user": ToolCategory.USERS,
    "update_user": ToolCategory.USERS,
    "delete_user": ToolCategory.USERS,
    "get_current_user": ToolCategory.USERS,
    "get_organization": ToolCategory.ORGANIZATIONS,
    "search_organizations": ToolCategory.ORGANIZATIONS,
    "create_organization": ToolCategory.ORGANIZATIONS,
    "update_organization": ToolCategory.ORGANIZATIONS,
    "delete_organization": ToolCategory.ORGANIZATIONS,
    "get_group": ToolCategory.GROUPS,
    "list_groups": ToolCategory.GROUPS,
    "create_group": ToolCategory.GROUPS,
    "get_ticket_states": ToolCategory.ADMIN,
    "get_priorities": ToolCategory.ADMIN,
    "list_tags": ToolCategory.ADMIN,
    "health_check": ToolCategory.SYSTEM,
    "get_server_info": ToolCategory.SYSTEM,
    "get_allowed_tools": ToolCategory.SYSTEM,
}

REGISTERED_TOOLS: frozenset[str] = frozenset(TOOL_CATEGORIES)


def _parse_permission_name(raw: str) -> Permission:
    mapping = {
        "denied": Permission.DENIED,
        "read_only": Permission.READ_ONLY,
        "read-only": Permission.READ_ONLY,
        "read": Permission.READ_ONLY,
        "write": Permission.WRITE,
        "admin": Permission.ADMIN,
    }
    key = raw.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unknown MCP_DEFAULT_PERMISSION: {raw}")
    return mapping[key]


@dataclass
class AccessPolicy:
    """Access policy configuration."""

    default_permission: Permission = Permission.READ_ONLY
    category_permissions: dict[ToolCategory, Permission] = field(default_factory=dict)
    tool_permissions: dict[str, Permission] = field(default_factory=dict)
    denied_tools: set[str] = field(default_factory=set)
    allowed_groups: set[str] | None = None
    allowed_organizations: set[int] | None = None
    rate_limit_per_minute: int = 60
    audit_log_path: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize the policy."""
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
        self._call_times: list[float] = []

    def can_execute(self, tool_name: str) -> bool:
        """Check if a tool can be executed."""
        if self._is_denied(tool_name):
            return False
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

    def consume_rate_limit(self) -> None:
        """Raise PermissionError when the sliding-window limit is exceeded."""
        limit = self.policy.rate_limit_per_minute
        if limit <= 0:
            return
        now = time.time()
        self._call_times = [stamp for stamp in self._call_times if now - stamp < 60.0]
        if len(self._call_times) >= limit:
            raise PermissionError(
                f"Rate limit exceeded ({limit} calls/minute). Retry after a short wait."
            )
        self._call_times.append(now)

    def _is_denied(self, tool_name: str) -> bool:
        """Check if tool is explicitly denied."""
        if tool_name in self.policy.denied_tools:
            return True
        return any(fnmatch.fnmatch(tool_name, pattern) for pattern in self.policy.denied_tools)

    def _get_permission(self, tool_name: str) -> Permission:
        """Get the permission level for a tool."""
        if tool_name in self.policy.tool_permissions:
            return self.policy.tool_permissions[tool_name]
        category = TOOL_CATEGORIES.get(tool_name, ToolCategory.ALL)
        if category in self.policy.category_permissions:
            return self.policy.category_permissions[category]
        return self.policy.default_permission

    def filter_ticket(self, ticket: dict[str, Any]) -> dict[str, Any] | None:
        """Filter ticket data based on policy restrictions."""
        if self.policy.allowed_groups is not None:
            group = ticket.get("group", "")
            if isinstance(group, dict):
                group = group.get("name", "")
            if group not in self.policy.allowed_groups:
                return None

        if self.policy.allowed_organizations is not None:
            org_id = ticket.get("organization_id", ticket.get("organizationId"))
            if org_id is not None and int(org_id) not in self.policy.allowed_organizations:
                return None

        return ticket

    def assert_group_allowed(self, group_name: str) -> None:
        """Deny writes to groups outside MCP_ALLOWED_GROUPS."""
        if self.policy.allowed_groups is None:
            return
        if group_name not in self.policy.allowed_groups:
            raise PermissionError(f"Access denied for group: {group_name}")

    def assert_ticket_allowed(self, ticket: dict[str, Any]) -> None:
        """Raise if the ticket is outside group/org scope."""
        if self.filter_ticket(ticket) is None:
            raise PermissionError("Access denied for this ticket")

    def log_access(
        self,
        tool_name: str,
        allowed: bool,
        client_info: dict[str, Any] | None = None,
    ) -> None:
        """Log an access attempt to memory, stderr, and optional audit file."""
        entry = {
            "timestamp": time.time(),
            "tool": tool_name,
            "allowed": allowed,
            "permission": self._get_permission(tool_name).name,
            "client": client_info or {},
        }
        self._access_log.append(entry)
        logger.info("mcp_access", **entry)
        path = self.policy.audit_log_path
        if path:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")

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
        allowed_categories_str = os.getenv("MCP_ALLOWED_CATEGORIES", "all")
        allowed_categories = {cat.strip().lower() for cat in allowed_categories_str.split(",")}

        default_raw = os.getenv("MCP_DEFAULT_PERMISSION", "write")
        default_permission = _parse_permission_name(default_raw)

        category_permissions: dict[ToolCategory, Permission] = {}
        if "all" in allowed_categories:
            category_permissions[ToolCategory.ALL] = default_permission
        else:
            for cat in ToolCategory:
                if cat == ToolCategory.ALL:
                    continue
                if cat.value in allowed_categories:
                    category_permissions[cat] = default_permission
                else:
                    category_permissions[cat] = Permission.DENIED

        denied_tools_str = os.getenv("MCP_DENIED_TOOLS", "")
        denied_tools = {tool.strip() for tool in denied_tools_str.split(",") if tool.strip()}

        allowed_groups_str = os.getenv("MCP_ALLOWED_GROUPS", "")
        allowed_groups = None
        if allowed_groups_str:
            allowed_groups = {g.strip() for g in allowed_groups_str.split(",") if g.strip()}

        orgs_str = os.getenv("MCP_ALLOWED_ORGANIZATIONS", "")
        allowed_organizations = None
        if orgs_str:
            allowed_organizations = {
                int(part.strip()) for part in orgs_str.split(",") if part.strip()
            }

        rate_raw = os.getenv("MCP_RATE_LIMIT_PER_MINUTE", "60")
        rate_limit_per_minute = int(rate_raw)

        audit_log_path = os.getenv("MCP_AUDIT_LOG_PATH") or None

        policy = AccessPolicy(
            default_permission=default_permission,
            category_permissions=category_permissions,
            denied_tools=denied_tools,
            allowed_groups=allowed_groups,
            allowed_organizations=allowed_organizations,
            rate_limit_per_minute=rate_limit_per_minute,
            audit_log_path=audit_log_path,
        )
        return cls(policy)

    def get_allowed_tools(self) -> list[str]:
        """Get list of all allowed registered tools based on current policy."""
        allowed = []
        for tool_name in REGISTERED_TOOLS:
            if self.can_execute(tool_name):
                allowed.append(tool_name)
        return sorted(allowed)

    def get_tool_info(self) -> list[dict[str, str]]:
        """Get detailed information about all registered tools and their permissions."""
        info = []
        for tool_name, category in sorted(TOOL_CATEGORIES.items()):
            permission = self._get_permission(tool_name)
            is_denied = self._is_denied(tool_name)
            info.append(
                {
                    "tool": tool_name,
                    "category": category.value,
                    "permission": permission.name,
                    "accessible": str(not is_denied and permission != Permission.DENIED),
                }
            )
        return info
