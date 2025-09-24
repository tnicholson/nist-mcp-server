# NIST MCP Server

A Model Context Protocol (MCP) server providing comprehensive access to NIST cybersecurity frameworks, controls, and OSCAL processing tools. This server enables AI assistants and applications to query, search, and analyze NIST security controls and frameworks through a standardized interface.

## Features

### 🔐 NIST SP 800-53 Rev 5 Controls
- Complete catalog of security controls with detailed descriptions
- Control family organization (AC, AU, AT, CM, CP, etc.)
- Control enhancements and implementation guidance
- Search controls by keyword, family, or ID
- Baseline control sets (Low, Moderate, High impact levels)

### 🛡️ NIST Cybersecurity Framework 2.0
- Complete CSF functions: Identify, Protect, Detect, Respond, Recover
- Categories and subcategories with detailed descriptions
- Framework core structure and relationships

### 🔗 Control Mappings
- SP 800-53 to CSF mappings
- Cross-reference controls with framework subcategories
- Bidirectional relationship analysis

### 📋 OSCAL Support
- JSON schema validation for OSCAL documents
- Support for catalogs, profiles, SSPs, assessment plans, and POA&Ms
- Example OSCAL documents for reference

### 🔍 Advanced Search & Analysis
- Keyword search across control content
- Family-based filtering and organization
- Control relationship mapping
- Baseline compliance checking

## Quick Start

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python package management. uv is significantly faster than pip and provides better dependency resolution.

### 1. Installation

#### Option A: Automated Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/nist-mcp.git
cd nist-mcp

# Run the installation script (installs uv, dependencies, and downloads data)
./scripts/install.sh
```

#### Option B: Manual Installation

```bash
# Clone the repository
git clone https://github.com/your-username/nist-mcp.git
cd nist-mcp

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with uv
uv sync --dev

# Or with pip (alternative)
pip install -e ".[dev]"
```

### 2. Download NIST Data

```bash
# Download official NIST data sources
python scripts/download_nist_data.py

# For verbose output
python scripts/download_nist_data.py --verbose

# Force re-download existing files
python scripts/download_nist_data.py --force
```

### 3. Run the Server

```bash
# Start the MCP server
nist-mcp

# Or run directly with Python
python -m nist_mcp.server
```

## MCP Tools Available

The server provides the following MCP tools for AI assistants:

### Control Management
- `list_controls()` - List all available NIST controls
- `get_control(control_id)` - Get detailed control information
- `search_controls(query, family, limit)` - Search controls by keyword
- `get_control_family(family)` - Get all controls in a family (e.g., "AC", "AU")
- `get_control_mappings(control_id)` - Get CSF mappings for a control
- `get_baseline_controls(baseline)` - Get controls for Low/Moderate/High baselines
- `control_relationships(control_id)` - Analyze control relationships and dependencies

### Advanced Analysis
- `gap_analysis(implemented_controls, target_baseline)` - Perform compliance gap analysis
- `risk_assessment_helper(control_ids)` - Assess risk coverage of control selection
- `compliance_mapping(framework, control_ids)` - Map to SOC2, ISO27001, etc.
- `analyze_control_coverage(control_ids)` - Analyze coverage across control families

### Cybersecurity Framework (CSF)
- `get_csf_framework()` - Get complete NIST CSF 2.0 structure
- `search_csf_subcategories(query, function)` - Search CSF subcategories
- `csf_to_controls_mapping(subcategory_id)` - Map CSF subcategories to controls

### OSCAL Processing
- `validate_oscal_document(document, document_type)` - Validate OSCAL documents
- Schema validation for catalogs, profiles, SSPs, assessment plans, POA&Ms
- Support for all major OSCAL document types with JSON Schema validation

## Project Structure

```
nist-mcp/
├── src/nist_mcp/           # Main package
│   ├── server.py           # MCP server implementation
│   ├── data/               # Data loading and caching
│   │   └── loader.py       # NIST data loader
│   ├── tools/              # MCP tools (future expansion)
│   └── utils/              # Utility functions
├── data/                   # NIST data sources
│   ├── nist-sources/       # Official NIST data
│   │   ├── sp800-53/       # SP 800-53 controls and baselines
│   │   ├── csf/            # Cybersecurity Framework data
│   │   └── mappings/       # Control-to-CSF mappings
│   ├── oscal-schemas/      # OSCAL JSON schemas
│   └── examples/           # Example OSCAL documents
├── scripts/                # Utility scripts
│   └── download_nist_data.py # Data download script
├── tools/                  # Additional control tools
│   └── control_tools.py    # Control management utilities
└── tests/                  # Test suite
```

## Data Sources

This project uses official public domain data from NIST:

### Primary Sources
- **NIST SP 800-53 Rev 5** - Security and Privacy Controls (Public Domain)
- **NIST Cybersecurity Framework 2.0** - Framework Core (Public Domain)
- **OSCAL Schemas v1.1.3** - Open Security Controls Assessment Language (Apache 2.0)

### Downloaded Content
- Complete SP 800-53 controls catalog (JSON/XML)
- Low, Moderate, and High baseline profiles
- CSF 2.0 functions, categories, and subcategories
- Control-to-CSF mappings
- OSCAL JSON schemas for all document types

## Development

### Setup Development Environment

```bash
# Install development dependencies
uv sync --dev

# Setup development environment (includes pre-commit hooks)
make setup-dev

# Or manually:
pre-commit install
```

### Testing

We use a comprehensive testing approach with multiple layers:

```bash
# Run all tests
make test

# Run specific test categories
make test-security      # Security and vulnerability tests
make test-quality       # Code quality and linting
make test-integration   # MCP integration tests
make test-performance   # Performance and load tests
make test-coverage      # Coverage analysis

# Code quality tools
make lint              # Ruff linting
make format            # Code formatting
make type-check        # MyPy type checking
make security          # Bandit + Safety security scans
```

### Code Quality Tools

- **uv**: Fast Python package manager (10-100x faster than pip)
- **Ruff**: Fast Python linter and formatter
- **Bandit**: Security vulnerability scanner
- **Safety**: Dependency vulnerability checker
- **MyPy**: Static type checking
- **pytest**: Testing framework with async support
- **Coverage**: Code coverage analysis

### Why uv?

We use [uv](https://docs.astral.sh/uv/) for package management because it:
- **10-100x faster** than pip for dependency resolution and installation
- **Better dependency resolution** with conflict detection
- **Reproducible builds** with lock files
- **Cross-platform compatibility** (Windows, macOS, Linux)
- **Drop-in replacement** for pip with better UX

### Adding New Tools

The MCP server is designed for extensibility. To add new tools:

1. Create tool functions in `src/nist_mcp/server.py`
2. Use the `@app.tool()` decorator
3. Add data loading logic to `data/loader.py` if needed
4. Update tests and documentation

## Configuration

### Data Path
By default, the server looks for data in the `data/` directory. You can specify a custom path:

```python
from nist_mcp.server import NISTMCPServer
server = NISTMCPServer(data_path="/custom/path/to/data")
```

### Logging
Configure logging level for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

MIT License - See LICENSE file for details.

### Third-Party Data Licenses
- NIST publications are in the public domain (U.S. Government Work)
- OSCAL schemas are licensed under Apache 2.0
- See `THIRD_PARTY_LICENSES/` directory for complete license information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and linting
6. Submit a pull request

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation in the `docs/` directory
- Review example usage in `data/examples/`