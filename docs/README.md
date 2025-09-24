# NIST MCP Server Documentation

This directory contains documentation for the NIST MCP Server project.

## Documentation Structure

- **API Reference**: Detailed documentation of MCP tools and functions
- **User Guide**: How to use the server with AI assistants
- **Developer Guide**: Contributing and extending the server
- **Data Sources**: Information about NIST data sources and licensing

## Quick Links

- [Main README](../README.md) - Project overview and quick start
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute
- [License Information](../THIRD_PARTY_LICENSES/) - Third-party licenses

## MCP Tools Reference

### Control Management Tools

#### `list_controls()`
Returns a list of all available NIST SP 800-53 controls.

**Returns**: `List[Dict[str, Any]]`
- Each control contains `id` and `title` fields

#### `get_control(control_id: str)`
Get detailed information for a specific control.

**Parameters**:
- `control_id`: The control identifier (e.g., "AC-1", "AU-2")

**Returns**: `Dict[str, Any]`
- Complete control information including parts, properties, and enhancements

#### `search_controls(query: str, family: str = None, limit: int = 10)`
Search controls by keyword.

**Parameters**:
- `query`: Search term to look for in control titles and content
- `family`: Optional control family filter (e.g., "AC", "AU")
- `limit`: Maximum number of results to return

**Returns**: `List[Dict[str, Any]]`
- List of matching controls with snippets

### Framework Tools

Access to NIST Cybersecurity Framework 2.0 data including functions, categories, and subcategories.

### OSCAL Tools

Tools for working with OSCAL (Open Security Controls Assessment Language) documents and schemas.

## Usage Examples

### With Claude or other AI assistants

```
You: "Show me all access control policies"
AI: Uses search_controls("access control policy") to find relevant controls

You: "What are the requirements for AC-1?"
AI: Uses get_control("AC-1") to get detailed control information

You: "List all audit controls"
AI: Uses search_controls("", family="AU") to get all AU family controls
```

## Data Sources

The server uses official NIST public domain data:
- NIST SP 800-53 Rev 5 controls
- NIST Cybersecurity Framework 2.0
- OSCAL schemas and examples

All data is automatically downloaded and cached locally.