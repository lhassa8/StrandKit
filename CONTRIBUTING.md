# Contributing to StrandKit

First off, thank you for considering contributing to StrandKit! 🎉

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please be respectful and constructive in all interactions.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the behavior
- **Expected behavior**
- **Actual behavior**
- **Environment details** (Python version, OS, AWS region)
- **Code samples** or error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case**: Why is this enhancement useful?
- **Proposed solution**: How should it work?
- **Alternatives considered**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** if applicable
4. **Update documentation** if needed
5. **Ensure all tests pass**
6. **Submit a pull request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/StrandKit.git
cd StrandKit

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black mypy ruff

# Run tests
python examples/test_imports.py
```

## Coding Standards

### Python Style

- Follow **PEP 8** style guide
- Use **Black** for code formatting (line length: 88)
- Use **type hints** for function signatures
- Write **comprehensive docstrings** (Google style)

```python
def example_function(param: str, optional: int = 0) -> Dict[str, Any]:
    """
    Brief description of what the function does.

    Longer description if needed, explaining behavior, edge cases, etc.

    Args:
        param: Description of param
        optional: Description of optional parameter (default: 0)

    Returns:
        Dictionary containing:
        {
            "key": "value",
            "count": 42
        }

    Example:
        >>> result = example_function("test")
        >>> print(result["count"])
        42
    """
    return {"key": param, "count": optional}
```

### Documentation

- **Docstrings**: All public functions must have docstrings
- **Type hints**: Use type hints for all function parameters and return values
- **Examples**: Include usage examples in docstrings
- **Comments**: Explain "why" not "what" in code comments

### Testing

- Write tests for new features
- Ensure existing tests pass
- Use mocked AWS clients (no real API calls in tests)

```python
# Example test structure
def test_get_lambda_logs():
    """Test that get_lambda_logs handles missing log groups"""
    # Arrange
    mock_client = create_mock_client()

    # Act
    result = get_lambda_logs("test-function", aws_client=mock_client)

    # Assert
    assert result["total_events"] == 0
    assert "warning" in result
```

## Project Structure

```
strandkit/
├── core/           # Core utilities and base classes
├── tools/          # AWS tool implementations
├── agents/         # Agent templates
├── prompts/        # System prompts for agents
└── cli/            # Command-line interface

examples/           # Usage examples
tests/              # Test suite
```

## Adding a New Tool

1. **Create the tool** in appropriate module (e.g., `strandkit/tools/`)
2. **Add comprehensive docstring** with:
   - Description
   - Parameters with types
   - Return value structure
   - Usage examples
   - Tool schema (for LLM consumption)
3. **Export in `__init__.py`**
4. **Add example** in `examples/`
5. **Update README.md**

Example:

```python
def new_tool(
    param: str,
    aws_client: Optional[AWSClient] = None
) -> Dict[str, Any]:
    """
    Description of what this tool does.

    Args:
        param: Parameter description
        aws_client: Optional AWSClient instance

    Returns:
        Dictionary containing:
        {
            "result": "value",
            "status": "success"
        }

    Example:
        >>> result = new_tool("test")
        >>> print(result["status"])
        success

    Tool Schema (for LLMs):
        {
            "name": "new_tool",
            "description": "Brief description",
            "parameters": {
                "param": {
                    "type": "string",
                    "required": true
                }
            }
        }
    """
    # Implementation
    pass
```

## Git Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line should be 50 characters or less
- Reference issues and PRs liberally

Examples:

```
Add get_iam_policy tool for policy analysis

- Implement policy retrieval from IAM
- Add risk assessment logic
- Include usage examples

Fixes #42
```

## Review Process

1. **Automated checks** must pass (linting, tests)
2. **Code review** by maintainer(s)
3. **Documentation** must be updated if needed
4. **Changes requested** may need to be addressed

## Areas for Contribution

We especially welcome contributions in:

- 🔧 **New AWS tools** (IAM, Cost Explorer, EC2, etc.)
- 🤖 **Agent templates** (Cost Analyst, Security Auditor, etc.)
- 📖 **Documentation improvements**
- 🧪 **Tests** (unit tests, integration tests)
- 🐛 **Bug fixes**
- ⚡ **Performance optimizations**

## Questions?

- Open an issue with the `question` label
- Start a discussion in GitHub Discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to StrandKit! 🚀
