"""Attachment upload/download tests."""

import base64
from typing import Any
from unittest.mock import MagicMock, patch

import respx
from httpx import Response

from zammad_mcp_server.client import ZammadClient
from zammad_mcp_server.models import ArticleCreateRequest, ArticleType, AttachmentUpload


def test_create_article_sends_mime_type_key(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post("http://test-zammad.local/api/v1/ticket_articles").mock(
        return_value=Response(
            201,
            json={
                "id": 9,
                "ticketId": 1,
                "body": "file",
                "attachments": [{"id": 3, "filename": "a.txt"}],
            },
        )
    )
    client = ZammadClient()
    request = ArticleCreateRequest(
        ticket_id=1,
        body="file",
        type=ArticleType.NOTE,
        attachments=[
            AttachmentUpload(
                filename="a.txt", data=base64.b64encode(b"hi").decode(), mime_type="text/plain"
            )
        ],
    )
    article = client.create_article(request)
    assert article.id == 9
    sent = route.calls.last.request
    assert b"mime-type" in sent.content


def test_get_article_attachment_bytes(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("http://test-zammad.local/api/v1/ticket_attachment/1/2/3").mock(
        return_value=Response(200, content=b"hello")
    )
    client = ZammadClient()
    data = client.get_article_attachment(1, 2, 3)
    assert data == b"hello"


def test_get_article_attachment_tool_as_text(unrestricted_controller: Any) -> None:
    with (
        patch("zammad_mcp_server.server.get_client") as mock_get_client,
        patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller,
    ):
        mock_client = MagicMock()
        ticket = MagicMock()
        ticket.model_dump.return_value = {"id": 1, "group": "Support"}
        ticket.get_group_name.return_value = "Support"
        mock_client.get_ticket.return_value = ticket
        mock_client.get_article_attachment.return_value = b"plain"
        mock_get_client.return_value = mock_client
        mock_get_controller.return_value = unrestricted_controller
        from zammad_mcp_server.server import get_article_attachment

        result = get_article_attachment(1, 2, 3, as_text=True)
        assert result["text"] == "plain"
        assert result["size"] == 5
