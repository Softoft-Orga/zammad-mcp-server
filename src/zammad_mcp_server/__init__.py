"""Zammad MCP Server - A powerful MCP server for Zammad ticket system."""

__version__ = "0.2.0"
__author__ = "Softoft"
__email__ = "tobias.bueck@openticketai.com"

from zammad_mcp_server.access_control import AccessController, Permission
from zammad_mcp_server.client import ZammadClient
from zammad_mcp_server.models import (
    Article,
    Group,
    Organization,
    SearchResult,
    Ticket,
    TicketStats,
    User,
)

__all__ = [
    "Ticket",
    "User",
    "Organization",
    "Group",
    "Article",
    "TicketStats",
    "SearchResult",
    "ZammadClient",
    "AccessController",
    "Permission",
]
