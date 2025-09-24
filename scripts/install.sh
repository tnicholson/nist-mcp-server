#!/bin/bash
# NIST MCP Server Installation Script

set -e

echo "🚀 NIST MCP Server Installation"
echo "==============================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the shell configuration to make uv available
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi
    
    # Add to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    
    echo "✅ uv installed successfully"
else
    echo "✅ uv is already installed"
fi

# Verify uv installation
if ! command -v uv &> /dev/null; then
    echo "❌ uv installation failed. Falling back to pip..."
    echo "📦 Installing with pip..."
    pip install -e ".[dev]"
else
    echo "📦 Installing dependencies with uv..."
    uv sync --dev
fi

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️  pre-commit not found, skipping hook installation"
fi

# Download NIST data
echo "📥 Downloading NIST data..."
python scripts/download_nist_data.py

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Run tests: make test"
echo "  2. Start server: make run-server"
echo "  3. See all commands: make help"