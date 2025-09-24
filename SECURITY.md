# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in the NIST MCP Server, please report it responsibly:

1. **Do not** create a public GitHub issue for security vulnerabilities
2. Email the maintainers directly (see contact information in README)
3. Include a detailed description of the vulnerability
4. Provide steps to reproduce the issue if possible
5. Include any relevant code or configuration

## Security Considerations

### Data Sources
- This project uses only public domain NIST data sources
- No sensitive or classified information is included
- All data sources are downloaded from official NIST repositories

### Network Security
- The MCP server runs locally and does not expose network services by default
- Data downloads use HTTPS connections to official NIST sources
- No user data is transmitted or stored

### Dependencies
- We regularly update dependencies to address security vulnerabilities
- Use `pip-audit` or similar tools to check for known vulnerabilities
- Pre-commit hooks help catch potential security issues

### Best Practices
- Run the server in a sandboxed environment when possible
- Keep dependencies updated
- Review any custom data sources for security implications
- Use proper access controls for the data directory

## Response Timeline

- **Initial Response**: Within 48 hours of receiving a report
- **Assessment**: Within 1 week of initial response
- **Fix Development**: Depends on severity and complexity
- **Public Disclosure**: After fix is available and deployed

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 0.1.1 → 0.1.2)
- Documented in the changelog
- Announced in release notes
- Tagged with security labels in GitHub releases