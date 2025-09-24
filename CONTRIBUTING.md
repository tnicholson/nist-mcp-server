# Contributing to NIST MCP Server

Thank you for your interest in contributing to the NIST MCP Server! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment

```bash
# Clone your fork
git clone https://github.com/your-username/nist-mcp.git
cd nist-mcp

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Download NIST data
python scripts/download_nist_data.py
```

## Development Workflow

1. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the coding standards below

3. Run comprehensive tests:
   ```bash
   # Run all tests (recommended)
   make test

   # Or run specific test categories
   make test-quality      # Code quality and linting
   make test-security     # Security scans
   make test-integration  # MCP integration tests

   # Format and lint code
   make format
   make lint
   make type-check

   # Run pre-commit hooks
   pre-commit run --all-files
   ```

4. Commit your changes with a clear commit message

5. Push to your fork and submit a pull request

## Coding Standards

### Python Code Style
- Follow PEP 8 style guidelines
- Use Black for code formatting (line length: 88)
- Use isort for import sorting
- Include type hints for all functions and methods
- Write docstrings for all public functions, classes, and modules

### Code Quality
- Maintain test coverage for new features
- Use meaningful variable and function names
- Keep functions focused and small
- Add comments for complex logic

### Testing
- Write unit tests for all new functionality
- Use pytest for testing framework
- Mock external dependencies in tests
- Aim for high test coverage

## Project Structure

```
nist-mcp/
├── src/nist_mcp/           # Main package
│   ├── server.py           # MCP server implementation
│   ├── data/               # Data loading and caching
│   ├── tools/              # MCP tools
│   └── utils/              # Utility functions
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── data/                   # NIST data sources
└── docs/                   # Documentation
```

## Adding New MCP Tools

To add a new MCP tool:

1. Add the tool function to `src/nist_mcp/server.py`
2. Use the `@app.tool()` decorator
3. Include proper type hints and docstrings
4. Add corresponding tests
5. Update documentation

Example:
```python
@app.tool()
async def new_tool(parameter: str) -> Dict[str, Any]:
    """Description of what the tool does"""
    # Implementation here
    return result
```

## Data Sources and Licensing

This project uses public domain data from NIST:
- NIST SP 800-53 Rev 5 (Public Domain)
- NIST Cybersecurity Framework 2.0 (Public Domain)
- OSCAL Schemas (Apache 2.0)

When adding new data sources:
- Ensure they are properly licensed for redistribution
- Document the source and license
- Add appropriate attribution

## Documentation

- Update README.md for significant changes
- Add docstrings to all public APIs
- Include examples in docstrings where helpful
- Update type hints when changing function signatures

## Submitting Pull Requests

1. Ensure your code passes all tests and linting
2. Update documentation as needed
3. Add tests for new functionality
4. Write a clear pull request description
5. Reference any related issues

### Pull Request Checklist

- [ ] All tests pass (`make test`)
- [ ] Code is properly formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Security scans pass (`make security`)
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] No security vulnerabilities introduced

## Reporting Issues

When reporting issues:
- Use the GitHub issue tracker
- Include a clear description of the problem
- Provide steps to reproduce the issue
- Include relevant error messages and logs
- Specify your environment (Python version, OS, etc.)

## Questions and Support

- Open an issue for bug reports or feature requests
- Check existing issues before creating new ones
- Be respectful and constructive in discussions

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.