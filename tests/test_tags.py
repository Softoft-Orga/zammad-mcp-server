"""Tag tool and client tests."""

from typing import Any
from unittest.mock import MagicMock, patch

import respx
from httpx import Response

from zammad_mcp_server.client import ZammadClient


def test_client_list_add_remove_tags(respx_mock: respx.MockRouter) -> None:
    base = "http://test-zammad.local/api/v1"
    respx_mock.get(f"{base}/tags").mock(return_value=Response(200, json={"tags": ["bug"]}))
    respx_mock.post(f"{base}/tags/add").mock(return_value=Response(201, json=True))
    respx_mock.delete(f"{base}/tags/remove").mock(return_value=Response(201, json=True))
    respx_mock.get(f"{base}/tag_list").mock(
        return_value=Response(200, json=[{"id": 1, "name": "bug", "count": 3}])
    )
    respx_mock.post(f"{base}/links/add").mock(return_value=Response(201, json={"id": 1}))
    respx_mock.post(f"{base}/ticket_merge").mock(return_value=Response(200, json={"result": "ok"}))
    client = ZammadClient()
    assert client.list_ticket_tags(5) == ["bug"]
    assert client.add_ticket_tag(5, "urgent") is True
    assert client.remove_ticket_tag(5, "bug") is True
    catalog = client.list_tags()
    assert catalog[0]["name"] == "bug"
    assert client.link_tickets(1, 2)["id"] == 1
    assert client.merge_tickets(1, 2)["result"] == "ok"


def test_add_ticket_tag_tool(unrestricted_controller: Any) -> None:
    with (
        patch("zammad_mcp_server.server.get_client") as mock_get_client,
        patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller,
    ):
        mock_client = MagicMock()
        ticket = MagicMock()
        ticket.model_dump.return_value = {"id": 1, "group": "Support"}
        ticket.get_group_name.return_value = "Support"
        mock_client.get_ticket.return_value = ticket
        mock_client.add_ticket_tag.return_value = True
        mock_get_client.return_value = mock_client
        mock_get_controller.return_value = unrestricted_controller
        from zammad_mcp_server.server import add_ticket_tag

        result = add_ticket_tag(1, "urgent")
        assert result["success"] is True
        mock_client.add_ticket_tag.assert_called_once_with(1, "urgent")
