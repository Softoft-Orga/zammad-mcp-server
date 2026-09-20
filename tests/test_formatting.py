"""Tests for HTML-to-text article formatting."""

from zammad_mcp_server.formatting import html_to_text, with_body_plain


def test_html_to_text_strips_tags() -> None:
    plain = html_to_text("<p>Hello <b>world</b></p><script>alert(1)</script>")
    assert "Hello" in plain
    assert "world" in plain
    assert "alert" not in plain
    assert "<p>" not in plain


def test_html_to_text_plain_passthrough() -> None:
    assert html_to_text("just text") == "just text"


def test_with_body_plain_nested_articles(monkeypatch: object) -> None:
    payload = {
        "id": 1,
        "body": "<p>Outer</p>",
        "articles": [{"id": 2, "body": "<div>Inner</div>"}],
    }
    result = with_body_plain(payload)
    assert result["body_plain"] == "Outer"
    articles = result["articles"]
    assert isinstance(articles, list)
    inner = articles[0]
    assert isinstance(inner, dict)
    assert inner["body_plain"] == "Inner"
