"""
Basic tests for CI pipeline
"""

import pytest
from pathlib import Path


def test_imports():
    """Test that basic imports work"""
    from nist_mcp.server import NISTMCPServer
    from nist_mcp.data.loader import NISTDataLoader
    
    assert NISTMCPServer is not None
    assert NISTDataLoader is not None


def test_server_creation():
    """Test that server can be created"""
    from nist_mcp.server import NISTMCPServer
    
    server = NISTMCPServer()
    assert server is not None
    assert server.data_path is not None


def test_data_loader_creation():
    """Test that data loader can be created"""
    from nist_mcp.data.loader import NISTDataLoader
    
    loader = NISTDataLoader(Path("/tmp"))
    assert loader is not None
    assert loader.data_path == Path("/tmp")


def test_package_structure():
    """Test that package structure is correct"""
    import nist_mcp
    import nist_mcp.server
    import nist_mcp.data.loader
    
    assert hasattr(nist_mcp.server, 'NISTMCPServer')
    assert hasattr(nist_mcp.data.loader, 'NISTDataLoader')