"""Integration smoke tests against a live Zammad (docker/)."""

import os

import pytest

from zammad_mcp_server import server as mcp_server
from zammad_mcp_server.access_control import (
    AccessController,
    AccessPolicy,
    Permission,
    ToolCategory,
)
from zammad_mcp_server.client import ZammadClient

pytestmark = pytest.mark.integration


def _live_url() -> str:
    return os.getenv("ZAMMAD_URL", "http://localhost:8080")


@pytest.fixture()
def live_client() -> ZammadClient:
    token = os.getenv("ZAMMAD_HTTP_TOKEN")
    if not token:
        pytest.skip("ZAMMAD_HTTP_TOKEN required for integration tests")
    return ZammadClient(url=_live_url(), http_token=token)


@pytest.fixture()
def live_session(live_client: ZammadClient) -> None:
    mcp_server._client = live_client  # noqa: SLF001
    mcp_server._access_controller = AccessController(
        AccessPolicy(
            default_permission=Permission.ADMIN,
            category_permissions={ToolCategory.ALL: Permission.ADMIN},
            rate_limit_per_minute=0,
        )
    )
    yield
    mcp_server._client = None
    mcp_server._access_controller = None


def test_health_check_live(live_session: None) -> None:
    result = mcp_server.health_check()
    assert result["mcp_server"] == "healthy"
    assert result["zammad_connection"]["status"] == "healthy"


def test_ticket_tags_live(live_session: None, live_client: ZammadClient) -> None:
    groups = live_client.list_groups()
    group_name = groups[0].name
    created = mcp_server.create_ticket(
        title="MCP integration tag test",
        group=group_name,
        customer="nicole.braun@zammad.org",
        article_body="hello",
    )
    ticket_id = int(created["id"])
    mcp_server.add_ticket_tag(ticket_id, "mcp-integration")
    listed = mcp_server.list_ticket_tags(ticket_id)
    assert "mcp-integration" in listed["tags"]


def test_create_article_attachment_live(live_session: None, live_client: ZammadClient) -> None:
    groups = live_client.list_groups()
    created = mcp_server.create_ticket(
        title="MCP integration attachment",
        group=groups[0].name,
        customer="nicole.braun@zammad.org",
        article_body="with file",
    )
    ticket_id = int(created["id"])
    article = mcp_server.create_article(
        ticket_id=ticket_id,
        body="see attach",
        attachments=[
            {"filename": "note.txt", "data": "aGVsbG8=", "mime-type": "text/plain"},
        ],
    )
    assert article["id"]


def test_summarize_ticket_live(live_session: None, live_client: ZammadClient) -> None:
    groups = live_client.list_groups()
    created = mcp_server.create_ticket(
        title="MCP integration summarize",
        group=groups[0].name,
        customer="nicole.braun@zammad.org",
        article_body="<p>Need help</p>",
    )
    summary = mcp_server.summarize_ticket(int(created["id"]))
    assert "Need help" in summary["thread_plain"]
    assert summary["article_count"] >= 1
