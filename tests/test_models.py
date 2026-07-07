"""Tests for Zammad MCP Server models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from zammad_mcp_server.models import (
    Article,
    ArticleCreateRequest,
    ArticleType,
    Group,
    Organization,
    OrganizationCreateRequest,
    PriorityBrief,
    StateBrief,
    Ticket,
    TicketCreateRequest,
    TicketPriority,
    TicketState,
    TicketStats,
    TicketUpdateRequest,
    User,
    UserBrief,
    UserCreateRequest,
)


class TestTicketModel:
    """Test suite for Ticket model."""

    def test_ticket_creation(self) -> None:
        """Test basic ticket creation."""
        ticket = Ticket(
            id=1,
            title="Test Ticket",
            group="Users",
            state="open",
            priority="2 normal",
        )
        assert ticket.id == 1
        assert ticket.title == "Test Ticket"
        assert ticket.group == "Users"

    def test_ticket_with_objects(self) -> None:
        """Test ticket with nested objects."""
        ticket = Ticket(
            id=1,
            title="Test Ticket",
            group=GroupBrief(id=1, name="Users"),
            state=StateBrief(id=2, name="open", state_type="open"),
            priority=PriorityBrief(id=2, name="2 normal"),
            owner=UserBrief(id=1, firstname="Agent", lastname="User", email="agent@test.com"),
        )
        assert isinstance(ticket.group, GroupBrief)
        assert ticket.group.name == "Users"
        assert ticket.get_group_name() == "Users"
        assert ticket.get_state_name() == "open"
        assert ticket.get_priority_name() == "2 normal"

    def test_ticket_with_mixed_fields(self) -> None:
        """Test ticket with both object and string representations."""
        ticket_data = {
            "id": 1,
            "title": "Test Ticket",
            "group": {"id": 1, "name": "Users"},
            "state": "open",  # String representation
            "priority": {"id": 2, "name": "2 normal"},
            "owner": "Agent User",  # String representation
        }
        ticket = Ticket.model_validate(ticket_data)
        assert ticket.get_group_name() == "Users"
        assert ticket.get_state_name() == "open"
        assert ticket.owner == "Agent User"

    def test_ticket_state_helpers(self) -> None:
        """Test ticket state helper methods."""
        ticket = Ticket(
            id=1,
            title="Test",
            state=StateBrief(id=1, name="new", state_type="new"),
            priority="2 normal",
        )
        assert ticket.get_state_name() == "new"
        assert ticket.get_priority_name() == "2 normal"

    def test_ticket_validation_error(self) -> None:
        """Test that invalid data raises validation error."""
        with pytest.raises(ValidationError):
            Ticket(id="not-an-int", title="Test")  # type: ignore


class TestUserModel:
    """Test suite for User model."""

    def test_user_creation(self) -> None:
        """Test basic user creation."""
        user = User(
            id=1,
            login="testuser",
            email="test@example.com",
            firstname="Test",
            lastname="User",
        )
        assert user.id == 1
        assert user.email == "test@example.com"
        assert user.get_full_name() == "Test User"

    def test_user_full_name_variations(self) -> None:
        """Test full name generation with various inputs."""
        user1 = User(id=1, firstname="John", lastname="Doe", email="john@example.com")
        assert user1.get_full_name() == "John Doe"

        user2 = User(id=2, email="onlyemail@example.com")
        assert user2.get_full_name() == "onlyemail@example.com"

        user3 = User(id=3, login="onlylogin")
        assert user3.get_full_name() == "onlylogin"

        user4 = User(id=4)
        assert user4.get_full_name() == "Unknown"

    def test_user_with_organization(self) -> None:
        """Test user with organization."""
        user_data = {
            "id": 1,
            "firstname": "John",
            "lastname": "Doe",
            "organization": {"id": 1, "name": "Test Corp"},
        }
        user = User.model_validate(user_data)
        assert user.organization is not None


class TestArticleModel:
    """Test suite for Article model."""

    def test_article_creation(self) -> None:
        """Test basic article creation."""
        article = Article(
            id=1,
            ticket_id=100,
            subject="Test Article",
            body="This is the article body",
            type="note",
            internal=False,
        )
        assert article.id == 1
        assert article.ticket_id == 100
        assert article.subject == "Test Article"
        assert article.internal is False

    def test_article_internal_default(self) -> None:
        """Test that internal defaults to False."""
        article = Article(id=1, ticket_id=100)
        assert article.internal is False


    def test_article_accepts_zammad_snake_case_ticket_id(self) -> None:
        """Test article parsing from Zammad API response format."""
        article = Article.model_validate({
            "id": 1,
            "ticket_id": 100,
            "body": "This is the article body",
        })

        assert article.ticket_id == 100

    def test_article_accepts_camel_case_ticket_id(self) -> None:
        """Test article parsing remains compatible with camelCase ticketId."""
        article = Article.model_validate({
            "id": 1,
            "ticketId": 100,
            "body": "This is the article body",
        })

        assert article.ticket_id == 100


class TestOrganizationModel:
    """Test suite for Organization model."""

    def test_organization_creation(self) -> None:
        """Test basic organization creation."""
        org = Organization(
            id=1,
            name="Test Corp",
            shared=True,
            active=True,
        )
        assert org.id == 1
        assert org.name == "Test Corp"
        assert org.shared is True


class TestGroupModel:
    """Test suite for Group model."""

    def test_group_creation(self) -> None:
        """Test basic group creation."""
        group = Group(
            id=1,
            name="Support",
            active=True,
            user_ids=[1, 2, 3],
        )
        assert group.id == 1
        assert group.name == "Support"
        assert group.user_ids == [1, 2, 3]


class TestTicketStats:
    """Test suite for TicketStats model."""

    def test_stats_creation(self) -> None:
        """Test stats creation."""
        stats = TicketStats(
            total=100,
            open=20,
            closed=70,
            pending=5,
            new=5,
            by_group={"Support": 60, "Sales": 40},
            by_priority={"1 low": 20, "2 normal": 70, "3 high": 10},
        )
        assert stats.total == 100
        assert stats.by_group is not None
        assert stats.by_group["Support"] == 60


class TestRequestModels:
    """Test suite for request/creation models."""

    def test_ticket_create_request(self) -> None:
        """Test ticket creation request validation."""
        request = TicketCreateRequest(
            title="New Ticket",
            group="Support",
            customer="customer@example.com",
            article_body="Initial description",
        )
        assert request.title == "New Ticket"
        assert request.article_type == ArticleType.NOTE

    def test_ticket_create_request_validation(self) -> None:
        """Test that empty title raises error."""
        with pytest.raises(ValidationError):
            TicketCreateRequest(title="", group="Support")

    def test_ticket_update_request(self) -> None:
        """Test ticket update request."""
        request = TicketUpdateRequest(
            title="Updated Title",
            state=TicketState.OPEN,
        )
        assert request.title == "Updated Title"
        assert request.state == TicketState.OPEN

    def test_article_create_request(self) -> None:
        """Test article creation request."""
        request = ArticleCreateRequest(
            ticket_id=100,
            body="Article content",
            subject="Response",
            internal=True,
        )
        assert request.ticket_id == 100
        assert request.internal is True

    def test_user_create_request(self) -> None:
        """Test user creation request."""
        request = UserCreateRequest(
            email="newuser@example.com",
            firstname="New",
            lastname="User",
        )
        assert request.email == "newuser@example.com"

    def test_user_create_request_email_validation(self) -> None:
        """Test email validation in user creation."""
        with pytest.raises(ValidationError):
            UserCreateRequest(email="invalid-email")

    def test_organization_create_request(self) -> None:
        """Test organization creation request."""
        request = OrganizationCreateRequest(
            name="New Org",
            domain="neworg.com",
        )
        assert request.name == "New Org"
        assert request.domain == "neworg.com"


class TestEnums:
    """Test suite for enum models."""

    def test_ticket_state_enum(self) -> None:
        """Test ticket state enum values."""
        assert TicketState.NEW.value == "new"
        assert TicketState.OPEN.value == "open"
        assert TicketState.CLOSED.value == "closed"

    def test_ticket_priority_enum(self) -> None:
        """Test priority enum values."""
        assert TicketPriority.LOW.value == "1 low"
        assert TicketPriority.NORMAL.value == "2 normal"
        assert TicketPriority.HIGH.value == "3 high"

    def test_article_type_enum(self) -> None:
        """Test article type enum values."""
        assert ArticleType.EMAIL.value == "email"
        assert ArticleType.NOTE.value == "note"
        assert ArticleType.PHONE.value == "phone"
