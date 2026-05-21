"""Zammad MCP Server - A powerful MCP server for Zammad ticket system."""

__version__ = "0.1.1"
__author__ = "Open Ticket AI"
__email__ = "tobias.bueck@openticketai.com"

from zammad_mcp_server.models import (
    Ticket,
    User,
    Organization,
    Group,
    Article,
    TicketStats,
    SearchResult,
)
from zammad_mcp_server.client import ZammadClient
from zammad_mcp_server.access_control import AccessController, Permission

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
