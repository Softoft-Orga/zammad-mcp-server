# Zammad MCP Server Dockerfile
FROM python:3.11-slim

LABEL maintainer="Open Ticket AI <tobias.bueck@openticketai.com>"
LABEL description="MCP Server for Zammad Helpdesk System"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8000 \
    MCP_TRANSPORT=http

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# TCP listen check — FastMCP HTTP has no /health route.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('127.0.0.1',8000),2); s.close()"

CMD ["zammad-mcp-server", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
