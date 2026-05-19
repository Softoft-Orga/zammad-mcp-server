# Zammad MCP Server Dockerfile
FROM python:3.11-slim

LABEL maintainer="Open Ticket AI <tobias.bueck@openticketai.com>"
LABEL description="MCP Server for Zammad Helpdesk System"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastmcp>=2.0.0 \
    pydantic>=2.0.0 \
    httpx>=0.27.0 \
    structlog>=24.1.0 \
    cachetools>=5.3.0 \
    python-dotenv>=1.0.0

# Copy source code
COPY src/ ./src/

# Install the package
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for SSE transport
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (stdio for local, override for SSE)
CMD ["zammad-mcp-server"]
