# Publishing to PyPI

Package name: **`zammad-mcp-server`**  
PyPI: https://pypi.org/project/zammad-mcp-server/

## One-time setup (maintainers)

### 1. Create a PyPI account

Register at https://pypi.org/account/register/ and enable 2FA.

### 2. Trusted publishing (recommended)

On https://pypi.org/manage/project/zammad-mcp-server/settings/publishing/ (after the first upload) or via **Add a new pending publisher** before first release:

| Field | Value |
| --- | --- |
| PyPI project name | `zammad-mcp-server` |
| Owner | `Softoft-Orga` |
| Repository | `zammad-mcp-server` |
| Workflow name | `workflow.yml` |
| Environment | (leave empty) |

GitHub Actions will publish on **GitHub Release published** using OIDC (no long-lived API token in the repo).

### 3. Manual publish (alternative)

Create an API token at https://pypi.org/manage/account/token/ (scope: project `zammad-mcp-server`).

```bash
cd zammad-mcp-server
uv build
UV_PUBLISH_TOKEN=pypi-xxxxxxxx uv publish
```

On Windows PowerShell:

```powershell
$env:UV_PUBLISH_TOKEN = "pypi-xxxxxxxx"
uv build
uv publish
```

## Release checklist

1. Bump `version` in `pyproject.toml` and `src/zammad_mcp_server/__init__.py`.
2. Commit and push to `main`.
3. Create a GitHub release (tag `v0.1.0`) and publish it — CI runs `.github/workflows/workflow.yml`.
4. Verify: `uvx zammad-mcp-server` (with `ZAMMAD_URL` / `ZAMMAD_HTTP_TOKEN` set).

## User install (after publish)

```bash
pip install zammad-mcp-server
# or
uv tool install zammad-mcp-server
# or run without installing
uvx zammad-mcp-server
```

Claude Desktop / Cursor:

```json
{
  "mcpServers": {
    "zammad": {
      "command": "uvx",
      "args": ["zammad-mcp-server"],
      "env": {
        "ZAMMAD_URL": "https://your-zammad.example.com",
        "ZAMMAD_HTTP_TOKEN": "your_token"
      }
    }
  }
}
```
