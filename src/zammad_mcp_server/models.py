"""Pydantic models for Zammad MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TicketState(str, Enum):
    """Ticket state values."""

    NEW = "new"
    OPEN = "open"
    PENDING_REMINDER = "pending reminder"
    PENDING_CLOSE = "pending close"
    CLOSED = "closed"
    MERGED = "merged"
    REMOVED = "removed"


class TicketPriority(str, Enum):
    """Ticket priority values."""

    LOW = "1 low"
    NORMAL = "2 normal"
    HIGH = "3 high"
    CRITICAL = "critical"


class ArticleType(str, Enum):
    """Article type values."""

    EMAIL = "email"
    PHONE = "phone"
    WEB = "web"
    CHAT = "chat"
    NOTE = "note"
    TWITTER = "twitter"
    FACEBOOK = "facebook"


class Visibility(str, Enum):
    """Article visibility."""

    INTERNAL = "internal"
    PUBLIC = "public"


class StateBrief(BaseModel):
    """Brief state information."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    state_type: str = Field(alias="stateType")


class PriorityBrief(BaseModel):
    """Brief priority information."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str


class GroupBrief(BaseModel):
    """Brief group information."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str


class UserBrief(BaseModel):
    """Brief user information."""

    model_config = ConfigDict(extra="allow")

    id: int
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    login: str | None = None


class OrganizationBrief(BaseModel):
    """Brief organization information."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str


class Article(BaseModel):
    """Zammad article (ticket message/comment)."""

    model_config = ConfigDict(extra="allow")

    id: int
    ticket_id: int = Field(alias="ticketId")
    type: str | None = None
    sender: str | None = None
    subject: str | None = None
    body: str | None = None
    from_address: str | None = Field(alias="from", default=None)
    to: str | None = None
    cc: str | None = None
    internal: bool = False
    created_at: datetime | None = Field(alias="createdAt", default=None)
    updated_at: datetime | None = Field(alias="updatedAt", default=None)
    created_by: UserBrief | str | None = Field(alias="createdBy", default=None)
    updated_by: UserBrief | str | None = Field(alias="updatedBy", default=None)

    @field_validator("created_by", "updated_by", mode="before")
    @classmethod
    def parse_user_field(cls, v: Any) -> Any:
        """Handle both object and string representations."""
        if isinstance(v, dict):
            return UserBrief.model_validate(v)
        return v


class Ticket(BaseModel):
    """Zammad ticket model."""

    model_config = ConfigDict(extra="allow")

    id: int
    number: str | None = None
    title: str
    group: GroupBrief | str | None = None
    owner: UserBrief | str | None = None
    customer: UserBrief | str | None = None
    state: StateBrief | str | None = None
    priority: PriorityBrief | str | None = None
    subject: str | None = None
    article_count: int | None = Field(alias="articleCount", default=None)
    articles: list[Article] | None = None
    created_at: datetime | None = Field(alias="createdAt", default=None)
    updated_at: datetime | None = Field(alias="updatedAt", default=None)
    closed_at: datetime | None = Field(alias="closeAt", default=None)
    pending_time: datetime | None = Field(alias="pendingTime", default=None)
    first_response_at: datetime | None = Field(alias="firstResponseAt", default=None)

    @field_validator("group", "owner", "customer", "state", "priority", mode="before")
    @classmethod
    def parse_expandable_field(cls, v: Any) -> Any:
        """Handle both object and string representations from API."""
        if isinstance(v, dict):
            field_name = cls.model_fields.get("group")  # type: ignore
            if "stateType" in v:
                return StateBrief.model_validate(v)
            elif "state_type" in v:
                return StateBrief.model_validate(v)
            elif field_name and field_name.alias == "group":
                return GroupBrief.model_validate(v)
            elif "firstname" in v or "lastname" in v:
                return UserBrief.model_validate(v)
        return v

    def get_state_name(self) -> str | None:
        """Get state name regardless of format."""
        if self.state is None:
            return None
        if isinstance(self.state, StateBrief):
            return self.state.name
        return str(self.state)

    def get_priority_name(self) -> str | None:
        """Get priority name regardless of format."""
        if self.priority is None:
            return None
        if isinstance(self.priority, PriorityBrief):
            return self.priority.name
        return str(self.priority)

    def get_group_name(self) -> str | None:
        """Get group name regardless of format."""
        if self.group is None:
            return None
        if isinstance(self.group, GroupBrief):
            return self.group.name
        return str(self.group)


class User(BaseModel):
    """Zammad user model."""

    model_config = ConfigDict(extra="allow")

    id: int
    login: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    organization: OrganizationBrief | str | None = None
    role_ids: list[int] | None = Field(alias="roleIds", default=None)
    active: bool = True
    created_at: datetime | None = Field(alias="createdAt", default=None)
    updated_at: datetime | None = Field(alias="updatedAt", default=None)

    @field_validator("organization", mode="before")
    @classmethod
    def parse_organization(cls, v: Any) -> Any:
        """Handle both object and string representations."""
        if isinstance(v, dict):
            return OrganizationBrief.model_validate(v)
        return v

    def get_full_name(self) -> str:
        """Get user's full name."""
        parts = [p for p in [self.firstname, self.lastname] if p]
        if parts:
            return " ".join(parts)
        return self.login or self.email or "Unknown"


class Organization(BaseModel):
    """Zammad organization model."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    shared: bool = True
    note: str | None = None
    active: bool = True
    domain_assignment: bool | None = Field(alias="domainAssignment", default=None)
    domain: str | None = None
    created_at: datetime | None = Field(alias="createdAt", default=None)
    updated_at: datetime | None = Field(alias="updatedAt", default=None)
    member_ids: list[int] | None = Field(alias="memberIds", default=None)


class Group(BaseModel):
    """Zammad group model."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    active: bool = True
    note: str | None = None
    created_at: datetime | None = Field(alias="createdAt", default=None)
    updated_at: datetime | None = Field(alias="updatedAt", default=None)
    user_ids: list[int] | None = Field(alias="userIds", default=None)


class TicketStats(BaseModel):
    """Ticket statistics."""

    model_config = ConfigDict(extra="allow")

    total: int
    open: int
    closed: int
    pending: int
    new: int
    escalated: int | None = None
    by_group: dict[str, int] | None = None
    by_priority: dict[str, int] | None = None


class SearchResult(BaseModel):
    """Generic search result wrapper."""

    model_config = ConfigDict(extra="allow")

    items: list[Any]
    total_count: int
    page: int
    per_page: int
    total_pages: int


class TicketCreateRequest(BaseModel):
    """Request model for creating a ticket."""

    model_config = ConfigDict(extra="allow")

    title: str = Field(..., min_length=1, max_length=500)
    group: str = Field(..., min_length=1)
    customer: str | None = None
    state: TicketState | None = None
    priority: TicketPriority | None = None
    article_subject: str | None = Field(None, max_length=500)
    article_body: str | None = None
    article_type: ArticleType = ArticleType.NOTE
    article_internal: bool = False


class TicketUpdateRequest(BaseModel):
    """Request model for updating a ticket."""

    model_config = ConfigDict(extra="allow")

    title: str | None = Field(None, max_length=500)
    group: str | None = None
    owner: str | None = None
    state: TicketState | None = None
    priority: TicketPriority | None = None
    pending_time: datetime | None = None


class ArticleCreateRequest(BaseModel):
    """Request model for creating an article."""

    model_config = ConfigDict(extra="allow")

    ticket_id: int = Field(..., gt=0)
    subject: str | None = Field(None, max_length=500)
    body: str = Field(..., min_length=1)
    type: ArticleType = ArticleType.NOTE
    internal: bool = False
    to: str | None = None
    cc: str | None = None


class UserCreateRequest(BaseModel):
    """Request model for creating a user."""

    model_config = ConfigDict(extra="allow")

    login: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    phone: str | None = None
    mobile: str | None = None
    organization: str | None = None
    password: str | None = None
    active: bool = True


class OrganizationCreateRequest(BaseModel):
    """Request model for creating an organization."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=500)
    shared: bool = True
    note: str | None = None
    domain: str | None = None
    active: bool = True
