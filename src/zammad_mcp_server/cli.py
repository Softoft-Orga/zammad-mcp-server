"""Command-line interface for the Zammad MCP Server."""

from __future__ import annotations

import argparse
import os
from typing import Any, Protocol


class RunnableServer(Protocol):
    """Minimal FastMCP run() surface used by the CLI."""

    def run(self, *args: Any, **kwargs: Any) -> None: ...


def parse_server_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse transport flags with environment-variable fallbacks."""
    parser = argparse.ArgumentParser(
        prog="zammad-mcp-server",
        description="MCP server for Zammad helpdesk (stdio, HTTP, or SSE).",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse"),
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="MCP transport (default: stdio; Docker uses http).",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_SERVER_HOST", "127.0.0.1"),
        help="Bind address for http/sse (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_SERVER_PORT", "8000")),
        help="Bind port for http/sse (default: 8000).",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("MCP_SERVER_PATH"),
        help="URL path for http (/mcp/) or sse (/sse/).",
    )
    return parser.parse_args(argv)


def default_http_path(transport: str) -> str:
    """FastMCP default path for a network transport."""
    if transport == "sse":
        return "/sse/"
    return "/mcp/"


def run_server(mcp: RunnableServer, args: argparse.Namespace) -> None:
    """Start FastMCP with the parsed transport options."""
    if args.transport == "stdio":
        mcp.run()
        return
    path = args.path if args.path else default_http_path(args.transport)
    mcp.run(transport=args.transport, host=args.host, port=args.port, path=path)
