#!/bin/bash
# setup_project.sh - Quick project setup script

echo "🚀 Setting up NIST MCP Server project..."

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p src/nist_mcp/tools
mkdir -p src/nist_mcp/data
mkdir -p src/nist_mcp/utils
mkdir -p data/nist-sources/sp800-53
mkdir -p data/nist-sources/csf
mkdir -p data/nist-sources/mappings
mkdir -p data/oscal-schemas
mkdir -p data/examples
mkdir -p tests
mkdir -p docs
mkdir -p scripts
mkdir -p docker
mkdir -p THIRD_PARTY_LICENSES

# Create __init__.py files
echo "📄 Creating Python package files..."
touch src/nist_mcp/__init__.py
touch src/nist_mcp/tools/__init__.py
touch src/nist_mcp/data/__init__.py
touch src/nist_mcp/utils/__init__.py
touch tests/__init__.py

# Create basic README.md if it doesn't exist
if [ ! -f README.md ]; then
    echo "📝 Creating README.md..."
    cat > README.md << 'EOF'
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
EOF
fi

# Create basic requirements.txt for immediate use
echo "📦 Creating requirements.txt..."
cat > requirements.txt << 'EOF'
mcp>=0.5.0
jsonschema>=4.0.0
lxml>=4.9.0
requests>=2.28.0
pydantic>=2.0.0
click>=8.0.0
rich>=12.0.0
aiohttp>=3.8.0
aiofiles>=23.0.0
EOF

# Create simple main server file
echo "🔧 Creating basic server structure..."
cat > src/nist_mcp/server.py << 'EOF'
#!/usr/bin/env python3
"""
NIST MCP Server - Main server implementation
"""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class NISTMCPServer:
    """Main NIST MCP Server implementation"""
    
    def __init__(self, data_path: Path = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data"
        self.data_path = data_path
        logger.info(f"NIST MCP Server initialized with data path: {data_path}")
    
    async def run(self):
        """Run the MCP server"""
        logger.info("🚀 NIST MCP Server starting...")
        # Server implementation will be added here
        print("NIST MCP Server is ready!")
        print(f"Data path: {self.data_path}")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Server stopped by user")

async def main():
    """Main entry point"""
    logging.basicConfig(level=logging.INFO)
    server = NISTMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Create basic data loader
cat > src/nist_mcp/data/loader.py << 'EOF'
"""
NIST Data Loader - Basic implementation
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class NISTDataLoader:
    """Handles loading NIST data sources"""
    
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        logger.info(f"Data loader initialized: {data_path}")
    
    async def initialize(self):
        """Initialize the data loader"""
        if not self.data_path.exists():
            logger.warning(f"Data path does not exist: {self.data_path}")
            self.data_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Data loader ready")
        return True

    async def load_controls(self) -> Dict[str, Any]:
        """Load NIST SP 800-53 controls"""
        # Implementation will be added
        return {"controls": []}
EOF

# Create basic download script
cat > scripts/download_nist_data.py << 'EOF'
#!/usr/bin/env python3
"""
Basic NIST data download script
"""

import asyncio
import logging
from pathlib import Path

async def download_all_data(data_path: Path = None):
    """Download NIST data sources"""
    if data_path is None:
        data_path = Path(__file__).parent.parent / "data"
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"📁 Creating data directories in: {data_path}")
    
    # Create directory structure
    directories = [
        "nist-sources/sp800-53",
        "nist-sources/csf", 
        "nist-sources/mappings",
        "oscal-schemas",
        "examples"
    ]
    
    for directory in directories:
        dir_path = data_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created: {directory}")
    
    # Create placeholder data files
    placeholder_files = {
        "nist-sources/sp800-53/controls.json": {"controls": []},
        "nist-sources/csf/framework-core.json": {"functions": []},
        "nist-sources/mappings/controls-to-csf.json": {"mappings": {}},
    }
    
    for file_path, content in placeholder_files.items():
        full_path = data_path / file_path
        with open(full_path, 'w') as f:
            import json
            json.dump(content, f, indent=2)
        logger.info(f"✅ Created placeholder: {file_path}")
    
    logger.info("🎉 Basic data structure created!")
    logger.info("Next: Add the full download implementation")

if __name__ == "__main__":
    asyncio.run(download_all_data())
EOF

chmod +x scripts/download_nist_data.py

echo "✅ Project structure created!"
echo ""
echo "🔄 Next steps:"
echo "1. Install dependencies: pip install -r requirements.txt"  
echo "2. Create basic data structure: python scripts/download_nist_data.py"
echo "3. Test basic server: python src/nist_mcp/server.py"
echo ""
echo "📁 Project structure:"
find . -type f -name "*.py" | head -10
echo "..."