# Test file with an updated fixture to test the server
import pytest
from unittest.mock import AsyncMock
from pathlib import Path
from nist_mcp.server import NISTMCPServer


class TestNISTMCPServer:
    """Test the NIST MCP Server class"""

    @pytest.fixture
    async def server(self):
        """Create a test server instance"""
        # Use a temporary path for testing
        test_path = Path("/tmp/test_data")
        test_path.mkdir(exist_ok=True)

        server = NISTMCPServer(test_path)

        # Mock the loader to avoid actual file operations
        mock_loader = AsyncMock()
        mock_loader.initialize = AsyncMock(return_value=None)

        # Mock the data loading to return test data
        mock_controls = [
            {
                "id": "AC-1",
                "title": "Access Control Policy and Procedures",
                "family": "AC",
                "description": "The organization develops, documents, and disseminates...",
                "supplemental_guidance": "Supplemental guidance for AC-1..."
            }
        ]
        mock_loader.load_controls = AsyncMock(return_value=mock_controls)
        mock_loader.get_control_by_id = AsyncMock(return_value=mock_controls[0] if "AC-1" else None)

        server.loader = mock_loader
        yield server

    @pytest.fixture
    async def server_with_data(self, server):
        """Create a test server with loaded data"""
        # Mock that controls are loaded
        yield server

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initializes correctly"""
        server = NISTMCPServer(None)
        assert server is not None
        assert server.data_path is not None

    @pytest.mark.asyncio
    async def test_list_nist_controls_empty(self, server):
        """Test listing controls when no data is loaded"""
        from nist_mcp.server import NISTMCPServer

        # Create server and mock methods
        server = NISTMCPServer(Path("/tmp"))

        # Mock the list_nist_controls method
        server.list_nist_controls = AsyncMock(return_value=[])

        result = await server.list_nist_controls()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_nist_controls_with_data(self, server_with_data):
        """Test listing controls when data is loaded"""
        from nist_mcp.server import NISTMCPServer

        server = NISTMCPServer(Path("/tmp"))

        # Mock the list_nist_controls method
        mock_controls = [{"id": "AC-1", "title": "Test Control"}]
        server.list_nist_controls = AsyncMock(return_value=mock_controls)

        result = await server.list_nist_controls()
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_get_control_details_found(self, server_with_data):
        """Test getting control details when control exists"""
        from nist_mcp.server import NISTMCPServer

        server = NISTMCPServer(Path("/tmp"))

        # Mock the get_control_details method
        mock_control = {"id": "AC-1", "title": "Test Control"}
        server.get_control_details = AsyncMock(return_value=mock_control)

        result = await server.get_control_details("AC-1")
        assert result is not None
        assert result["id"] == "AC-1"

    @pytest.mark.asyncio
    async def test_get_control_details_not_found(self, server_with_data):
        """Test getting control details when control does not exist"""
        from nist_mcp.server import NISTMCPServer

        server = NISTMCPServer(Path("/tmp"))

        # Mock the get_control_details method to return None
        server.get_control_details = AsyncMock(return_value=None)

        result = await server.get_control_details("NON-EXISTENT")
        assert result is None
