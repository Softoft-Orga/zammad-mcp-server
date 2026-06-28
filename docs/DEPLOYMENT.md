# Deployment Guide

This guide covers various deployment options for the Zammad MCP Server, from local development to production cloud environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Cloud Run (Google Cloud)](#cloud-run-google-cloud)
- [AWS Lambda](#aws-lambda)
- [Railway](#railway)
- [Fly.io](#flyio)
- [Environment Configuration](#environment-configuration)
- [Security Considerations](#security-considerations)

## Quick Start

### Prerequisites

- Python 3.11 or higher
- A running Zammad instance (local or remote; **6.0+**, tested with **7.1**)
- API token from Zammad (Profile → Token Access)

### Minimal Setup

```bash
# Install the server
pip install zammad-mcp-server

# Set environment variables
export ZAMMAD_URL=https://your-zammad.com
export ZAMMAD_HTTP_TOKEN=your_token

# Run the server
zammad-mcp-server
```

## Local Development

### Using Docker Compose

We provide a complete Zammad development environment. Default image: **Zammad 7.1**.
Override with `ZAMMAD_VERSION` in `docker/.env` (see [COMPATIBILITY.md](COMPATIBILITY.md)
and [docker/README.md](../docker/README.md)):

```bash
cd docker
cp .env.example .env   # optional: set ZAMMAD_VERSION=6.5, 7.0, etc.
docker-compose up -d

# Wait for initialization (2-3 minutes)
docker-compose logs -f zammad-init

# Access Zammad at http://localhost:8080
# Default: admin@example.com / admin
```

The MCP server itself is unchanged — it connects to any Zammad **6.0+** instance via
the REST API. The dev stack simply tracks the current Zammad release we test against.

### Running the Server Locally

```bash
# Clone the repository
git clone https://github.com/Softoft-Orga/zammad-mcp-server.git
cd zammad-mcp-server

# Install dependencies
pip install -e ".[dev]"

# Run with stdio (for Claude Desktop)
zammad-mcp-server

# Run with SSE transport (for web clients)
zammad-mcp-server --transport sse --port 8000
```

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

**macOS:**
```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**Configuration:**
```json
{
  "mcpServers": {
    "zammad": {
      "command": "zammad-mcp-server",
      "env": {
        "ZAMMAD_URL": "http://localhost:8080",
        "ZAMMAD_HTTP_TOKEN": "your_token"
      }
    }
  }
}
```

## Docker Deployment

### Building the Image

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir fastmcp pydantic httpx structlog cachetools

# Copy source
COPY src/ ./src/

# Install the package
RUN pip install -e .

# Environment variables (can be overridden)
ENV MCP_SERVER_HOST=0.0.0.0
ENV MCP_SERVER_PORT=8000

EXPOSE 8000

CMD ["zammad-mcp-server", "--transport", "sse"]
```

Build and run:
```bash
# Build
docker build -t zammad-mcp-server .

# Run with environment variables
docker run -p 8000:8000 \
  -e ZAMMAD_URL=https://your-zammad.com \
  -e ZAMMAD_HTTP_TOKEN=your_token \
  zammad-mcp-server
```

### Docker Compose with Environment

```yaml
# docker-compose.mcp.yml
version: '3.8'

services:
  zammad-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ZAMMAD_URL=${ZAMMAD_URL}
      - ZAMMAD_HTTP_TOKEN=${ZAMMAD_HTTP_TOKEN}
      - MCP_ALLOWED_CATEGORIES=all
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run:
```bash
docker-compose -f docker-compose.mcp.yml up -d
```

## Cloud Run (Google Cloud)

Cloud Run is ideal for hosting MCP servers with its automatic scaling and pay-per-use pricing.

### Prerequisites

- Google Cloud SDK (`gcloud`)
- Project with Cloud Run API enabled
- Artifact Registry or Docker Hub access

### Deployment Steps

1. **Build and Push Container:**

```bash
# Set variables
PROJECT_ID=your-gcp-project
REGION=us-central1
SERVICE_NAME=zammad-mcp-server

# Build with Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Or build locally and push
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME
```

2. **Deploy to Cloud Run:**

```bash
# Create secrets in Secret Manager first
gcloud secrets create zammad-url --data-file=- <<< "https://your-zammad.com"
gcloud secrets create zammad-token --data-file=- <<< "your_token"

# Deploy
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --set-secrets ZAMMAD_URL=zammad-url:latest,ZAMMAD_HTTP_TOKEN=zammad-token:latest \
  --set-env-vars MCP_ALLOWED_CATEGORIES=all,LOG_LEVEL=INFO \
  --min-instances=0 \
  --max-instances=10
```

3. **Configure Claude:**

```json
{
  "mcpServers": {
    "zammad-cloud": {
      "url": "https://your-service-url.a.run.app/sse"
    }
  }
}
```

### Cloud Run Service Account

For production, use a dedicated service account:

```bash
# Create service account
gcloud iam service-accounts create zammad-mcp-sa \
  --display-name "Zammad MCP Server"

# Grant secret access
gcloud secrets add-iam-policy-binding zammad-url \
  --member="serviceAccount:zammad-mcp-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding zammad-token \
  --member="serviceAccount:zammad-mcp-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Deploy with service account
gcloud run deploy $SERVICE_NAME \
  --service-account zammad-mcp-sa@$PROJECT_ID.iam.gserviceaccount.com \
  ...
```

## AWS Lambda

Deploy as a Lambda function for serverless operation.

### Prerequisites

- AWS CLI configured
- AWS SAM or Serverless Framework (optional)

### Lambda Handler

Create `lambda_handler.py`:

```python
"""AWS Lambda handler for Zammad MCP Server."""

import json
import os
from urllib.parse import urlparse

from zammad_mcp_server.server import mcp
from mangum import Mangum

# Configure for Lambda
os.environ["ZAMMAD_URL"] = os.environ.get("ZAMMAD_URL")
os.environ["ZAMMAD_HTTP_TOKEN"] = os.environ.get("ZAMMAD_HTTP_TOKEN")

# Create handler
handler = Mangum(mcp.app, lifespan="off")

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    return handler(event, context)
```

### Deployment Package

```bash
# Create deployment package
pip install zammad-mcp-server mangum -t package/
cp lambda_handler.py package/
cd package && zip -r ../deployment.zip .

# Deploy
aws lambda create-function \
  --function-name zammad-mcp-server \
  --runtime python3.11 \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://deployment.zip \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-role \
  --environment Variables="{ZAMMAD_URL=https://your-zammad.com,ZAMMAD_HTTP_TOKEN=your_token}" \
  --timeout 30 \
  --memory-size 512
```

### API Gateway Setup

```bash
# Create REST API
aws apigateway create-rest-api --name zammad-mcp-api

# Create resource and method (manual or via CloudFormation)
# ...

# Deploy
aws apigateway create-deployment \
  --rest-api-id YOUR_API_ID \
  --stage-name prod
```

### Serverless Framework (Recommended)

```yaml
# serverless.yml
service: zammad-mcp-server

provider:
  name: aws
  runtime: python3.11
  environment:
    ZAMMAD_URL: ${env:ZAMMAD_URL}
    ZAMMAD_HTTP_TOKEN: ${env:ZAMMAD_HTTP_TOKEN}
    MCP_ALLOWED_CATEGORIES: all

functions:
  mcp:
    handler: lambda_handler.lambda_handler
    timeout: 30
    memorySize: 512
    events:
      - http:
          path: /{proxy+}
          method: ANY
          cors: true

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true
    slim: true
```

Deploy:
```bash
npm install -g serverless
serverless plugin install -n serverless-python-requirements
serverless deploy
```

## Railway

Railway offers simple deployment with automatic HTTPS.

### Setup

1. Create a `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "zammad-mcp-server --transport sse --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. Push to GitHub and connect to Railway

3. Add environment variables in Railway dashboard:
   - `ZAMMAD_URL`
   - `ZAMMAD_HTTP_TOKEN`
   - `MCP_ALLOWED_CATEGORIES`

### Using Railway CLI

```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up

# View logs
railway logs
```

## Fly.io

Fly.io provides edge deployment with good performance.

### Setup

1. Install Fly CLI:

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

2. Create `fly.toml`:

```toml
app = "zammad-mcp-server"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[env]
  MCP_SERVER_HOST = "0.0.0.0"
  MCP_SERVER_PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
```

3. Deploy:

```bash
# Create app
fly apps create zammad-mcp-server

# Set secrets
fly secrets set ZAMMAD_URL=https://your-zammad.com
fly secrets set ZAMMAD_HTTP_TOKEN=your_token

# Deploy
fly deploy

# Open app
fly open
```

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ZAMMAD_URL` | Zammad instance URL | `https://helpdesk.company.com` |
| `ZAMMAD_HTTP_TOKEN` | API token for authentication | `abc123...` |

### Authentication Alternatives

Instead of `ZAMMAD_HTTP_TOKEN`, you can use:

```env
# OAuth2
ZAMMAD_OAUTH2_TOKEN=oauth_token_here

# Or basic auth
ZAMMAD_USERNAME=admin@example.com
ZAMMAD_PASSWORD=securepassword
```

### Access Control Variables

```env
# Allow all categories (default)
MCP_ALLOWED_CATEGORIES=all

# Allow specific categories only
MCP_ALLOWED_CATEGORIES=tickets,groups,system

# Deny dangerous operations
MCP_DENIED_TOOLS=delete_ticket,delete_user,delete_organization

# Restrict to specific groups
MCP_ALLOWED_GROUPS=Support,Sales

# Set read-only mode
MCP_ALLOWED_CATEGORIES=tickets,users,organizations,groups,system
# (Without admin category)
```

### Logging Variables

```env
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json         # json or console
CACHE_TTL_SECONDS=300   # Cache time-to-live
MAX_CACHE_SIZE=1000     # Maximum cache entries
```

## Security Considerations

### API Token Security

1. **Never commit tokens to git**
   ```bash
   # Add to .gitignore
   .env
   *.env
   secrets.json
   ```

2. **Use secret management in cloud deployments**
   - GCP: Secret Manager
   - AWS: Secrets Manager or Parameter Store
   - Railway: Built-in secrets
   - Fly.io: `fly secrets`

3. **Rotate tokens regularly**
   - Create new tokens in Zammad
   - Update in secret manager
   - Delete old tokens

### Network Security

1. **Use HTTPS for Zammad URL**
   ```env
   # Good
   ZAMMAD_URL=https://zammad.company.com
   
   # Avoid
   ZAMMAD_URL=http://zammad.company.com
   ```

2. **Restrict Zammad API access**
   - Create dedicated API user
   - Limit token permissions to required endpoints
   - Use IP restrictions if possible

3. **Cloud deployment security**
   ```bash
   # Enable HTTPS redirect
   fly deploy --env HTTPS_REDIRECT=true
   
   # Cloud Run uses HTTPS by default
   # Railway provides automatic HTTPS
   ```

### Access Control Best Practices

```env
# Production: Read-only for safety
MCP_ALLOWED_CATEGORIES=tickets,users,organizations,groups,system
MCP_DENIED_TOOLS=delete_*

# With write access: Deny destructive operations
MCP_ALLOWED_CATEGORIES=all
MCP_DENIED_TOOLS=delete_ticket,delete_user,delete_organization

# Admin access: Allow everything (use with caution)
MCP_ALLOWED_CATEGORIES=all
# (No MCP_DENIED_TOOLS)
```

### Audit Logging

Access is automatically logged. In production:

```python
# Export logs to centralized system
# GCP: Cloud Logging
gcloud logging read "resource.type=cloud_run_revision"

# AWS: CloudWatch Logs
aws logs tail /aws/lambda/zammad-mcp-server

# Railway: Dashboard or CLI
railway logs --tail
```

## Health Checks

All deployment methods should include health checks:

```python
# The server automatically responds to health checks
GET /health -> {"status": "healthy", "zammad_connection": {...}}
```

### Cloud Run Health Check

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
```

### Fly.io Health Check

```toml
[[services.http_checks]]
  interval = "30s"
  timeout = "5s"
  grace_period = "30s"
  method = "GET"
  path = "/health"
  protocol = "http"
```

## Troubleshooting

### Connection Issues

```bash
# Test Zammad connection
curl -H "Authorization: Token token=$ZAMMAD_HTTP_TOKEN" \
  "$ZAMMAD_URL/api/v1/ping"

# Check logs
docker logs <container_id>
gcloud logging read "resource.labels.service_name=zammad-mcp-server"
fly logs
```

### Performance Issues

```bash
# Increase memory/lambda timeout
aws lambda update-function-configuration \
  --function-name zammad-mcp-server \
  --timeout 60 \
  --memory-size 1024

# Enable caching
docker run -e CACHE_TTL_SECONDS=600 ...
```

## Production Checklist

- [ ] HTTPS enabled for Zammad connection
- [ ] API token stored in secret manager
- [ ] Access control configured appropriately
- [ ] Health checks configured
- [ ] Logging configured and aggregated
- [ ] Rate limiting enabled (if available)
- [ ] Backup strategy for configuration
- [ ] Monitoring and alerts set up
- [ ] Documentation for operators

---

For more help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an [issue](https://github.com/Softoft-Orga/zammad-mcp-server/issues).
