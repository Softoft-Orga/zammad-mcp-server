"""Zammad API client wrapper with enhanced functionality."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from cachetools import TTLCache

from zammad_mcp_server.models import (
    Article,
    ArticleCreateRequest,
    Group,
    GroupCreateRequest,
    Organization,
    OrganizationCreateRequest,
    SearchResult,
    Ticket,
    TicketCreateRequest,
    TicketStats,
    TicketUpdateRequest,
    User,
    UserCreateRequest,
)

logger = structlog.get_logger()


class ZammadClientError(Exception):
    """Base exception for Zammad client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(ZammadClientError):
    """Authentication failed."""

    pass


class NotFoundError(ZammadClientError):
    """Resource not found."""

    pass


class ZammadClient:
    """Enhanced Zammad API client."""

    def __init__(
        self,
        url: str | None = None,
        http_token: str | None = None,
        oauth2_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
        cache_ttl: int = 300,
        max_cache_size: int = 1000,
    ) -> None:
        """Initialize the Zammad client.

        Args:
            url: Zammad instance URL
            http_token: API token for authentication
            oauth2_token: OAuth2 token for authentication
            username: Username for basic auth
            password: Password for basic auth
            timeout: Request timeout in seconds
            cache_ttl: Cache time-to-live in seconds
            max_cache_size: Maximum cache entries
        """
        self.url = (url or os.getenv("ZAMMAD_URL", "")).rstrip("/")
        self.http_token = http_token or os.getenv("ZAMMAD_HTTP_TOKEN")
        self.oauth2_token = oauth2_token or os.getenv("ZAMMAD_OAUTH2_TOKEN")
        self.username = username or os.getenv("ZAMMAD_USERNAME")
        self.password = password or os.getenv("ZAMMAD_PASSWORD")
        self.timeout = timeout

        # Caches for static data
        self._groups_cache: TTLCache = TTLCache(maxsize=max_cache_size, ttl=cache_ttl)
        self._states_cache: TTLCache = TTLCache(maxsize=100, ttl=cache_ttl)
        self._priorities_cache: TTLCache = TTLCache(maxsize=100, ttl=cache_ttl)

        if not self.url:
            raise ValueError("Zammad URL is required")

        self._client: httpx.Client | None = None
        self._setup_client()

        logger.info(
            "zammad_client_initialized",
            url=self.url,
            auth_method=self._get_auth_method(),
        )

    def _get_auth_method(self) -> str:
        """Determine the authentication method being used."""
        if self.http_token:
            return "http_token"
        if self.oauth2_token:
            return "oauth2"
        if self.username and self.password:
            return "basic_auth"
        return "none"

    def _setup_client(self) -> None:
        """Set up the HTTP client with authentication."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Authentication priority: HTTP Token > OAuth2 > Basic Auth
        if self.http_token:
            headers["Authorization"] = f"Token token={self.http_token}"
        elif self.oauth2_token:
            headers["Authorization"] = f"Bearer {self.oauth2_token}"

        auth: tuple[str, str] | None = None
        if self.username and self.password and not self.http_token and not self.oauth2_token:
            auth = (self.username, self.password)

        self._client = httpx.Client(
            base_url=self.url,
            headers=headers,
            auth=auth,
            timeout=self.timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an HTTP request to the Zammad API."""
        if not self._client:
            raise RuntimeError("Client not initialized")

        url = f"/api/v1{path}"

        try:
            response = self._client.request(method, url, **kwargs)
            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed", 401)
            if e.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path}", 404)
            raise ZammadClientError(
                f"HTTP error {e.response.status_code}: {e.response.text}",
                e.response.status_code,
            )
        except httpx.RequestError as e:
            raise ZammadClientError(f"Request failed: {e}")

    def health_check(self) -> dict[str, Any]:
        """Check if the Zammad server is accessible."""
        try:
            result = self._request("GET", "/ping")
            return {"status": "healthy", "response": result}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def get_server_info(self) -> dict[str, Any]:
        """Get Zammad server information."""
        return self._request("GET", "/system/")  # type: ignore

    # Ticket operations

    def get_ticket(
        self,
        ticket_id: int,
        include_articles: bool = False,
        expand: bool = True,
    ) -> Ticket:
        """Get a single ticket by ID."""
        params: dict[str, str] = {}
        if expand:
            params["expand"] = "true"

        result = self._request("GET", f"/tickets/{ticket_id}", params=params)
        ticket_data: dict[str, Any] = result  # type: ignore

        if include_articles:
            articles = self.get_ticket_articles(ticket_id)
            ticket_data["articles"] = [a.model_dump() for a in articles]

        return Ticket.model_validate(ticket_data)

    def search_tickets(
        self,
        query: str | None = None,
        state: str | None = None,
        priority: str | None = None,
        group: str | None = None,
        owner: str | None = None,
        customer: str | None = None,
        page: int = 1,
        per_page: int = 100,
        expand: bool = True,
    ) -> SearchResult:
        """Search for tickets with various filters."""
        filters = []
        if query:
            filters.append(query)
        if state:
            filters.append(f"state.name:{state}")
        if priority:
            filters.append(f"priority.name:{priority}")
        if group:
            filters.append(f"group.name:{group}")
        if owner:
            filters.append(f"owner.email:{owner}")
        if customer:
            filters.append(f"customer.email:{customer}")

        search_query = " AND ".join(filters) if filters else "*"

        params: dict[str, str | int] = {
            "query": search_query,
            "page": page,
            "per_page": per_page,
        }
        if expand:
            params["expand"] = "true"

        result = self._request("GET", "/tickets/search", params=params)

        # Parse search results
        if isinstance(result, dict):
            tickets_data = result.get("tickets", [])
            total_count = result.get("tickets_count", len(tickets_data))
        else:
            tickets_data = result
            total_count = len(tickets_data)

        tickets = [Ticket.model_validate(t) for t in tickets_data]

        return SearchResult(
            items=tickets,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=(total_count + per_page - 1) // per_page,
        )

    def create_ticket(self, request: TicketCreateRequest) -> Ticket:
        """Create a new ticket."""
        data: dict[str, Any] = {
            "title": request.title,
            "group": request.group,
        }

        if request.customer:
            data["customer"] = request.customer
        if request.state:
            data["state"] = request.state.value
        if request.priority:
            data["priority"] = request.priority.value

        # Include initial article if provided
        if request.article_body:
            data["article"] = {
                "subject": request.article_subject or request.title,
                "body": request.article_body,
                "type": request.article_type.value,
                "internal": request.article_internal,
            }

        result = self._request("POST", "/tickets", json=data)
        return Ticket.model_validate(result)

    def update_ticket(
        self,
        ticket_id: int,
        request: TicketUpdateRequest,
    ) -> Ticket:
        """Update an existing ticket."""
        data: dict[str, Any] = {}

        if request.title:
            data["title"] = request.title
        if request.group:
            data["group"] = request.group
        if request.owner:
            data["owner"] = request.owner
        if request.state:
            data["state"] = request.state.value
        if request.priority:
            data["priority"] = request.priority.value
        if request.pending_time:
            data["pending_time"] = request.pending_time.isoformat()

        result = self._request("PUT", f"/tickets/{ticket_id}", json=data)
        return Ticket.model_validate(result)

    def delete_ticket(self, ticket_id: int) -> bool:
        """Delete a ticket."""
        self._request("DELETE", f"/tickets/{ticket_id}")
        return True

    def get_ticket_articles(self, ticket_id: int) -> list[Article]:
        """Get all articles for a ticket."""
        result = self._request("GET", f"/ticket_articles/by_ticket/{ticket_id}")

        if isinstance(result, dict):
            articles_data = result.get("ticket_articles", [])
        else:
            articles_data = result

        return [Article.model_validate(a) for a in articles_data]

    def create_article(self, request: ArticleCreateRequest) -> Article:
        """Create a new article on a ticket."""
        data: dict[str, Any] = {
            "ticket_id": request.ticket_id,
            "body": request.body,
            "type": request.type.value,
            "internal": request.internal,
        }

        if request.subject:
            data["subject"] = request.subject
        if request.to:
            data["to"] = request.to
        if request.cc:
            data["cc"] = request.cc

        result = self._request("POST", "/ticket_articles", json=data)
        return Article.model_validate(result)

    def get_ticket_stats(
        self,
        group: str | None = None,
        max_scan_pages: int = 10,
    ) -> TicketStats:
        """Get ticket statistics with pagination support."""
        import time

        start_time = time.time()

        total = 0
        open_count = 0
        closed_count = 0
        pending_count = 0
        new_count = 0
        by_group: dict[str, int] = {}
        by_priority: dict[str, int] = {}

        page = 1
        while page <= max_scan_pages:
            params: dict[str, str | int] = {
                "query": "*",
                "page": page,
                "per_page": 100,
                "expand": "true",
            }

            result = self._request("GET", "/tickets/search", params=params)

            if isinstance(result, dict):
                tickets_data = result.get("tickets", [])
            else:
                tickets_data = result

            if not tickets_data:
                break

            for ticket_data in tickets_data:
                total += 1

                # Count by state
                state = ticket_data.get("state", "")
                if isinstance(state, dict):
                    state = state.get("name", "")

                state_lower = str(state).lower()
                if "open" in state_lower:
                    open_count += 1
                elif "closed" in state_lower or "close" in state_lower:
                    closed_count += 1
                elif "pending" in state_lower:
                    pending_count += 1
                elif "new" in state_lower:
                    new_count += 1

                # Count by group
                group_data = ticket_data.get("group", "")
                if isinstance(group_data, dict):
                    group_name = group_data.get("name", "Unknown")
                else:
                    group_name = str(group_data) if group_data else "Unknown"

                if group is None or group_name == group:
                    by_group[group_name] = by_group.get(group_name, 0) + 1

                # Count by priority
                priority = ticket_data.get("priority", "")
                if isinstance(priority, dict):
                    priority_name = priority.get("name", "Unknown")
                else:
                    priority_name = str(priority) if priority else "Unknown"

                by_priority[priority_name] = by_priority.get(priority_name, 0) + 1

            # Check if we've reached the end
            if len(tickets_data) < 100:
                break

            page += 1

        elapsed_time = time.time() - start_time

        logger.info(
            "ticket_stats_calculated",
            total=total,
            open=open_count,
            closed=closed_count,
            pages_fetched=page,
            elapsed_seconds=elapsed_time,
        )

        return TicketStats(
            total=total,
            open=open_count,
            closed=closed_count,
            pending=pending_count,
            new=new_count,
            by_group=by_group if by_group else None,
            by_priority=by_priority if by_priority else None,
        )

    # User operations

    def get_user(self, user_id: int) -> User:
        """Get a user by ID."""
        result = self._request("GET", f"/users/{user_id}", params={"expand": "true"})
        return User.model_validate(result)

    def search_users(
        self,
        query: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> SearchResult:
        """Search for users."""
        params: dict[str, str | int] = {
            "page": page,
            "per_page": per_page,
            "expand": "true",
        }
        if query:
            params["query"] = query

        result = self._request("GET", "/users/search", params=params)

        if isinstance(result, dict):
            users_data = result.get("users", [])
            total_count = result.get("users_count", len(users_data))
        else:
            users_data = result
            total_count = len(users_data)

        users = [User.model_validate(u) for u in users_data]

        return SearchResult(
            items=users,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=(total_count + per_page - 1) // per_page,
        )

    def create_user(self, request: UserCreateRequest) -> User:
        """Create a new user."""
        data: dict[str, Any] = {
            "active": request.active,
        }

        if request.login:
            data["login"] = request.login
        if request.firstname:
            data["firstname"] = request.firstname
        if request.lastname:
            data["lastname"] = request.lastname
        if request.email:
            data["email"] = request.email
        if request.phone:
            data["phone"] = request.phone
        if request.mobile:
            data["mobile"] = request.mobile
        if request.organization:
            data["organization"] = request.organization
        if request.password:
            data["password"] = request.password

        result = self._request("POST", "/users", json=data)
        return User.model_validate(result)

    def update_user(self, user_id: int, **kwargs: Any) -> User:
        """Update a user."""
        result = self._request("PUT", f"/users/{user_id}", json=kwargs)
        return User.model_validate(result)

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        self._request("DELETE", f"/users/{user_id}")
        return True

    def get_current_user(self) -> User:
        """Get the currently authenticated user."""
        result = self._request("GET", "/users/me")
        return User.model_validate(result)

    # Organization operations

    def get_organization(self, org_id: int) -> Organization:
        """Get an organization by ID."""
        result = self._request("GET", f"/organizations/{org_id}", params={"expand": "true"})
        return Organization.model_validate(result)

    def search_organizations(
        self,
        query: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> SearchResult:
        """Search for organizations."""
        params: dict[str, str | int] = {
            "page": page,
            "per_page": per_page,
            "expand": "true",
        }
        if query:
            params["query"] = query

        result = self._request("GET", "/organizations/search", params=params)

        if isinstance(result, dict):
            orgs_data = result.get("organizations", [])
            total_count = result.get("organizations_count", len(orgs_data))
        else:
            orgs_data = result
            total_count = len(orgs_data)

        orgs = [Organization.model_validate(o) for o in orgs_data]

        return SearchResult(
            items=orgs,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=(total_count + per_page - 1) // per_page,
        )

    def create_organization(self, request: OrganizationCreateRequest) -> Organization:
        """Create a new organization."""
        data: dict[str, Any] = {
            "name": request.name,
            "shared": request.shared,
            "active": request.active,
        }

        if request.note:
            data["note"] = request.note
        if request.domain:
            data["domain"] = request.domain

        result = self._request("POST", "/organizations", json=data)
        return Organization.model_validate(result)

    def update_organization(self, org_id: int, **kwargs: Any) -> Organization:
        """Update an organization."""
        result = self._request("PUT", f"/organizations/{org_id}", json=kwargs)
        return Organization.model_validate(result)

    def delete_organization(self, org_id: int) -> bool:
        """Delete an organization."""
        self._request("DELETE", f"/organizations/{org_id}")
        return True

    # Group operations

    def get_group(self, group_id: int) -> Group:
        """Get a group by ID."""
        # Check cache first
        if group_id in self._groups_cache:
            return self._groups_cache[group_id]

        result = self._request("GET", f"/groups/{group_id}", params={"expand": "true"})
        group = Group.model_validate(result)

        self._groups_cache[group_id] = group
        return group

    def list_groups(self) -> list[Group]:
        """List all groups."""
        result = self._request("GET", "/groups", params={"expand": "true"})

        if isinstance(result, dict):
            groups_data = result.get("groups", [])
        else:
            groups_data = result

        groups = [Group.model_validate(g) for g in groups_data]

        # Update cache
        for group in groups:
            self._groups_cache[group.id] = group

        return groups

    def create_group(self, request: GroupCreateRequest) -> Group:
        """Create a new group."""
        data: dict[str, Any] = {
            "name": request.name,
            "active": request.active,
        }
        if request.note:
            data["note"] = request.note

        result = self._request("POST", "/groups", json=data)
        group = Group.model_validate(result)
        self._groups_cache[group.id] = group
        return group

    def get_ticket_states(self) -> list[dict[str, Any]]:
        """Get all available ticket states."""
        if "states" in self._states_cache:
            return self._states_cache["states"]  # type: ignore

        result = self._request("GET", "/ticket_states", params={"expand": "true"})

        if isinstance(result, dict):
            states = result.get("ticket_states", [])
        else:
            states = result

        self._states_cache["states"] = states  # type: ignore
        return states  # type: ignore

    def get_priorities(self) -> list[dict[str, Any]]:
        """Get all available priorities."""
        if "priorities" in self._priorities_cache:
            return self._priorities_cache["priorities"]  # type: ignore

        result = self._request("GET", "/ticket_priorities", params={"expand": "true"})

        if isinstance(result, dict):
            priorities = result.get("ticket_priorities", [])
        else:
            priorities = result

        self._priorities_cache["priorities"] = priorities  # type: ignore
        return priorities  # type: ignore

    def clear_caches(self) -> None:
        """Clear all caches."""
        self._groups_cache.clear()
        self._states_cache.clear()
        self._priorities_cache.clear()
        logger.info("caches_cleared")

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> ZammadClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
