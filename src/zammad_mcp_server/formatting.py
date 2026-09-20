"""Article body formatting for LLM-friendly MCP responses."""

from __future__ import annotations

import html
import os
import re
from html.parser import HTMLParser
from typing import Any


class _TextExtractor(HTMLParser):
    """Collect visible text from HTML, skipping script/style."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        joined = " ".join(self._chunks)
        joined = html.unescape(joined)
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n{3,}", "\n\n", joined)
        return joined.strip()


def html_to_text(body: str) -> str:
    """Convert HTML (or mixed) article bodies to plain text."""
    if not body:
        return ""
    if "<" not in body:
        return html.unescape(body).strip()
    parser = _TextExtractor()
    parser.feed(body)
    parser.close()
    extracted = parser.text()
    return extracted if extracted else html.unescape(re.sub(r"<[^>]+>", " ", body)).strip()


def strip_html_enabled() -> bool:
    """Whether tool responses should include body_plain (default on)."""
    raw = os.getenv("MCP_STRIP_HTML", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def with_body_plain(payload: dict[str, Any]) -> dict[str, Any]:
    """Add body_plain next to body when HTML stripping is enabled."""
    if not strip_html_enabled():
        return payload
    body = payload.get("body")
    if isinstance(body, str):
        payload["body_plain"] = html_to_text(body)
    articles = payload.get("articles")
    if isinstance(articles, list):
        updated: list[Any] = []
        for article in articles:
            if isinstance(article, dict):
                updated.append(with_body_plain(article))
            else:
                updated.append(article)
        payload["articles"] = updated
    return payload
