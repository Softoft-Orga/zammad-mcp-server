"""Coverage for remaining MCP tools, resources, and prompts."""

from typing import Any
from unittest.mock import MagicMock, patch

from zammad_mcp_server.access_control import (
    AccessController,
    AccessPolicy,
    Permission,
    ToolCategory,
)


def _ticket() -> MagicMock:
    ticket = MagicMock()
    ticket.model_dump.return_value = {"id": 1, "group": "Support", "title": "T"}
    ticket.get_group_name.return_value = "Support"
    return ticket


def test_link_merge_and_tags(unrestricted_controller: Any) -> None:
    with (
        patch("zammad_mcp_server.server.get_client") as mock_get_client,
        patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller,
    ):
        client = MagicMock()
        client.get_ticket.return_value = _ticket()
        client.link_tickets.return_value = {"ok": True}
        client.merge_tickets.return_value = {"ok": True}
        client.list_ticket_tags.return_value = ["a"]
        client.list_tags.return_value = [{"name": "a"}]
        client.remove_ticket_tag.return_value = True
        mock_get_client.return_value = client
        mock_get_controller.return_value = unrestricted_controller

        from zammad_mcp_server.server import (
            link_tickets,
            list_tags,
            list_ticket_tags,
            merge_tickets,
            remove_ticket_tag,
        )

        assert link_tickets(1, 2)["source_id"] == 1
        assert merge_tickets(1, 2)["target_id"] == 2
        assert list_ticket_tags(1)["tags"] == ["a"]
        assert list_tags()["count"] == 1
        assert remove_ticket_tag(1, "a")["success"] is True


def test_resources_and_prompts(unrestricted_controller: Any) -> None:
    with (
        patch("zammad_mcp_server.server.get_client") as mock_get_client,
        patch("zammad_mcp_server.server.get_access_controller") as mock_get_controller,
    ):
        client = MagicMock()
        ticket = _ticket()
        ticket.number = "1"
        ticket.title = "T"
        ticket.get_state_name.return_value = "open"
        ticket.get_priority_name.return_value = "2 normal"
        ticket.created_at = None
        article = MagicMock()
        article.subject = "s"
        article.type = "note"
        article.from_address = "a@b.c"
        article.internal = False
        article.body = "<p>Hi</p>"
        ticket.articles = [article]
        user = MagicMock()
        user.get_full_name.return_value = "Ada"
        user.email = "ada@example.com"
        user.login = "ada"
        user.phone = None
        user.mobile = None
        user.active = True
        user.created_at = None
        org = MagicMock()
        org.name = "Acme"
        org.shared = True
        org.active = True
        org.domain = None
        org.note = None
        client.get_ticket.return_value = ticket
        client.get_user.return_value = user
        client.get_ticket_states.return_value = [{"name": "open", "stateType": "open"}]
        client.get_priorities.return_value = [{"name": "2 normal"}]
        client.get_organization.return_value = org
        mock_get_client.return_value = client
        mock_get_controller.return_value = unrestricted_controller

        from zammad_mcp_server.server import (
            analyze_ticket,
            draft_response,
            escalation_summary,
            get_organization_resource,
            get_priorities_resource,
            get_states_resource,
            get_ticket_resource,
            get_user_resource,
            triage_queue,
        )

        assert "Ticket" in get_ticket_resource("1")
        assert "Ada" in get_user_resource("1")
        assert "open" in get_states_resource()
        assert "2 normal" in get_priorities_resource()
        assert "Acme" in get_organization_resource("1")
        assert "1" in analyze_ticket("1", "de")
        assert "internal" in draft_response("1", "en", "calm", "internal")
        assert "Support" in triage_queue("Support", "en")
        assert "pending" in escalation_summary("Support", "en")


def test_filter_ticket_by_organization() -> None:
    controller = AccessController(
        AccessPolicy(
            default_permission=Permission.READ_ONLY,
            allowed_organizations={5},
            rate_limit_per_minute=0,
            category_permissions={ToolCategory.ALL: Permission.READ_ONLY},
        )
    )
    assert controller.filter_ticket({"id": 1, "organization_id": 5}) is not None
    assert controller.filter_ticket({"id": 2, "organization_id": 9}) is None


def test_audit_log_file(tmp_path: Any, monkeypatch: Any) -> None:
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG_PATH", str(path))
    monkeypatch.setenv("MCP_ALLOWED_CATEGORIES", "all")
    monkeypatch.delenv("MCP_DENIED_TOOLS", raising=False)
    controller = AccessController.from_env()
    controller.log_access("get_ticket", True)
    assert path.read_text(encoding="utf-8")
