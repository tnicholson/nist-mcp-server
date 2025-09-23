# NIST MCP Server

A Model Context Protocol (MCP) server providing comprehensive access to NIST cybersecurity frameworks, controls, and OSCAL processing tools.

## Quick Start

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Download NIST data:
```bash
python scripts/download_nist_data.py
```

3. Run the server:
```bash
nist-mcp
```

## Features

- Complete NIST SP 800-53 Rev 5 Controls
- NIST Cybersecurity Framework 2.0
- OSCAL document processing
- Control mappings and assessments

## Data Sources
This project uses public domain data from:
- NIST SP 800-53 Rev 5 (Public Domain - U.S. Government Work)
- NIST Cybersecurity Framework 2.0 (Public Domain - U.S. Government Work)
- OSCAL Schemas (Apache 2.0 License)