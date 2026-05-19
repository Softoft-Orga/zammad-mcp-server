# Contributing to Zammad MCP Server

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Docker (optional, for local Zammad)

### Setup Steps

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/zammad-mcp-server.git
   cd zammad-mcp-server
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests and Checks

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=zammad_mcp_server --cov-report=html

# Run type checking
mypy src/zammad_mcp_server

# Run linting
ruff check src/
ruff format src/
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `style:` Code style changes (formatting)
- `chore:` Maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use Google-style docstrings

### Example

```python
def get_ticket(ticket_id: int, include_articles: bool = False) -> Ticket:
    """Get a specific ticket by ID.

    Args:
        ticket_id: The ID of the ticket to retrieve.
        include_articles: Whether to include all articles/messages.

    Returns:
        Ticket details including metadata and optionally articles.

    Raises:
        NotFoundError: If the ticket does not exist.
        AuthenticationError: If authentication fails.
    """
    # Implementation
```

## Testing Guidelines

### Writing Tests

- Use pytest for all tests
- Place tests in the `tests/` directory
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

### Test Example

```python
def test_get_ticket_success(mock_client: MagicMock) -> None:
    """Test getting a ticket successfully."""
    # Arrange
    mock_ticket = MagicMock()
    mock_ticket.model_dump.return_value = {"id": 1, "title": "Test"}
    mock_client.get_ticket.return_value = mock_ticket

    # Act
    result = get_ticket(1)

    # Assert
    assert result["id"] == 1
    assert result["title"] == "Test"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models.py

# Run with coverage report
pytest --cov=zammad_mcp_server --cov-report=term-missing

# Run integration tests only
pytest -m integration
```

## Adding New Tools

To add a new MCP tool:

1. **Define the tool in `server.py`:**

```python
@mcp.tool()
def my_new_tool(param: str) -> dict[str, Any]:
    """Description of what the tool does.
    
    Args:
        param: Description of the parameter.
        
    Returns:
        Description of the return value.
    """
    check_access("my_new_tool", Permission.READ_ONLY)
    client = get_client()
    
    result = client.some_operation(param)
    return result.model_dump()
```

2. **Update access control in `access_control.py`:**

```python
TOOL_CATEGORIES: dict[str, ToolCategory] = {
    # ... existing mappings
    "my_new_tool": ToolCategory.TICKETS,  # or appropriate category
}
```

3. **Add tests in `tests/test_server.py`:**

```python
def test_my_new_tool(unrestricted_controller: Any) -> None:
    """Test my new tool."""
    with patch("zammad_mcp_server.server.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        result = my_new_tool("test")
        assert result is not None
```

4. **Update documentation:**
   - Add to README.md tools list
   - Update ARCHITECTURE.md if significant

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of the function.
    
    Longer description if needed. Can span multiple lines
    and include additional context.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
        
    Returns:
        Description of the return value.
        
    Raises:
        ValueError: When param2 is negative.
        NotFoundError: When resource not found.
    """
```

### Updating README

When adding features:
1. Update the feature list
2. Add new tools to the tools table
3. Update configuration examples
4. Add to the roadmap if applicable

## Pull Request Process

1. **Before submitting:**
   - All tests pass
   - Code is formatted with ruff
   - Type checking passes with mypy
   - Documentation is updated

2. **PR Description should include:**
   - What changes were made
   - Why the changes were needed
   - How to test the changes
   - Any breaking changes

3. **Review Process:**
   - Maintainers will review within 48 hours
   - Address review comments
   - Keep commits clean and focused

## Reporting Issues

### Bug Reports

Include:
- Python version
- Zammad version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages/logs

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## Security Issues

**Do not open public issues for security vulnerabilities.**

Instead, email security concerns to: security@openticketai.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

## Questions?

- 📖 [Documentation](https://github.com/Softoft-Orga/zammad-mcp-server/tree/main/docs)
- 💬 [Discussions](https://github.com/Softoft-Orga/zammad-mcp-server/discussions)
- 🐛 [Issue Tracker](https://github.com/Softoft-Orga/zammad-mcp-server/issues)

Thank you for contributing!
