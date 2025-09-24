# NIST Data Directory

This directory contains NIST cybersecurity data sources used by the MCP server.

## Directory Structure

```
data/
├── nist-sources/           # Official NIST data (downloaded)
│   ├── sp800-53/          # SP 800-53 controls and baselines
│   ├── csf/               # Cybersecurity Framework data
│   └── mappings/          # Control-to-CSF mappings
├── oscal-schemas/         # OSCAL JSON schemas (downloaded)
└── examples/              # Example OSCAL documents
```

## Data Sources

### NIST SP 800-53 Rev 5
- **Source**: NIST OSCAL Content Repository
- **License**: Public Domain (U.S. Government Work)
- **Files**: 
  - `controls.json` - Complete controls catalog
  - `controls.xml` - XML format (fallback)
  - `*-baseline.json` - Low/Moderate/High baseline profiles

### NIST Cybersecurity Framework 2.0
- **Source**: NIST CSF 2.0 Publication
- **License**: Public Domain (U.S. Government Work)
- **Files**: `framework-core.json` - CSF functions, categories, subcategories

### OSCAL Schemas
- **Source**: NIST OSCAL Project
- **License**: Apache 2.0
- **Version**: v1.1.3
- **Files**: JSON schemas for all OSCAL document types

### Control Mappings
- **Source**: Generated from NIST mapping documents
- **License**: Public Domain
- **Files**: `controls-to-csf.json` - SP 800-53 to CSF mappings

## Downloading Data

Run the download script to fetch all required data:

```bash
# Download all data sources
python scripts/download_nist_data.py

# Force re-download
python scripts/download_nist_data.py --force

# Verbose output
python scripts/download_nist_data.py --verbose
```

## Data Updates

The NIST data sources are updated periodically. To get the latest versions:

1. Run the download script with `--force` flag
2. The server will automatically use the updated data on restart

## License Information

- **NIST Publications**: Public Domain (U.S. Government Work)
- **OSCAL Schemas**: Apache License 2.0
- See `../THIRD_PARTY_LICENSES/` for complete license texts

## Data Integrity

All downloaded JSON files are validated during the download process to ensure data integrity.