"""Tests for MCP transport CLI parsing."""

from argparse import Namespace
from typing import Any
from unittest.mock import MagicMock

from zammad_mcp_server.cli import default_http_path, parse_server_args, run_server


def test_parse_defaults() -> None:
    args = parse_server_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_parse_http_flags() -> None:
    args = parse_server_args(["--transport", "http", "--host", "0.0.0.0", "--port", "9000"])
    assert args.transport == "http"
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_parse_env_transport(monkeypatch: Any) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "sse")
    monkeypatch.setenv("MCP_SERVER_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_SERVER_PORT", "8123")
    args = parse_server_args([])
    assert args.transport == "sse"
    assert args.host == "0.0.0.0"
    assert args.port == 8123


def test_run_stdio_calls_run_without_kwargs() -> None:
    mcp = MagicMock()
    run_server(mcp, Namespace(transport="stdio", host="127.0.0.1", port=8000, path=None))
    mcp.run.assert_called_once_with()


def test_run_http_passes_bind_options() -> None:
    mcp = MagicMock()
    run_server(mcp, Namespace(transport="http", host="0.0.0.0", port=8000, path=None))
    mcp.run.assert_called_once_with(
        transport="http",
        host="0.0.0.0",
        port=8000,
        path=default_http_path("http"),
    )


def test_run_sse_default_path() -> None:
    mcp = MagicMock()
    run_server(mcp, Namespace(transport="sse", host="0.0.0.0", port=8000, path=None))
    kwargs = mcp.run.call_args.kwargs
    assert kwargs["path"] == "/sse/"
