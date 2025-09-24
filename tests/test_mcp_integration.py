"""
MCP Server Integration Tests

Tests for MCP-specific functionality and tool integration.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import json

from mcp.server import FastMCP
from nist_mcp.server import app, nist_server


class TestMCPIntegration:
    """Integration tests for MCP server functionality"""

    def test_mcp_app_creation(self):
        """Test that MCP app is properly created"""
        assert isinstance(app, FastMCP)
        assert app.name == "nist-mcp-server"

    @pytest.mark.asyncio
    async def test_server_lifespan(self):
        """Test server lifespan management"""
        # Mock the loader initialization
        with patch.object(
            nist_server.loader, "initialize", new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = None

            # Test lifespan context manager
            from nist_mcp.server import lifespan

            async with lifespan(app):
                mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_controls_tool(self):
        """Test the list_controls MCP tool"""
        sample_controls = [
            {"id": "AC-1", "title": "Access Control Policy and Procedures"},
            {"id": "AC-2", "title": "Account Management"},
        ]

        with patch.object(
            nist_server, "list_nist_controls", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = sample_controls

            # Import the tool function
            from nist_mcp.server import list_controls

            result = await list_controls()
            assert result == sample_controls
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_control_tool(self):
        """Test the get_control MCP tool"""
        sample_control = {
            "id": "AC-1",
            "title": "Access Control Policy and Procedures",
            "class": "SP800-53",
            "parts": [],
        }

        with patch.object(
            nist_server, "get_control_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = sample_control

            # Import the tool function
            from nist_mcp.server import get_control

            result = await get_control("AC-1")
            assert result == sample_control
            mock_get.assert_called_once_with("AC-1")

    @pytest.mark.asyncio
    async def test_get_control_tool_not_found(self):
        """Test get_control tool with non-existent control"""
        with patch.object(
            nist_server, "get_control_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = ValueError("Control AC-999 not found")

            from nist_mcp.server import get_control

            with pytest.raises(ValueError, match="Control AC-999 not found"):
                await get_control("AC-999")

    def test_mcp_tool_decorators(self):
        """Test that MCP tools are properly decorated"""
        # Check that tools are registered with the app
        tool_names = [tool.name for tool in app.tools]

        expected_tools = ["list_controls", "get_control"]
        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool {tool_name} not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_server_error_handling(self):
        """Test server error handling for various scenarios"""
        # Test with loader initialization failure
        with patch.object(
            nist_server.loader, "initialize", new_callable=AsyncMock
        ) as mock_init:
            mock_init.side_effect = FileNotFoundError("Data path not found")

            with pytest.raises(FileNotFoundError):
                await nist_server.loader.initialize()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent MCP tool requests"""
        import asyncio

        sample_controls = [{"id": "AC-1", "title": "Test Control"}]

        with patch.object(
            nist_server, "list_nist_controls", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = sample_controls

            from nist_mcp.server import list_controls

            # Make multiple concurrent requests
            tasks = [list_controls() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # All results should be the same
            for result in results:
                assert result == sample_controls

            # Function should be called 5 times
            assert mock_list.call_count == 5


class TestMCPToolValidation:
    """Tests for MCP tool input validation and error handling"""

    @pytest.mark.asyncio
    async def test_get_control_input_validation(self):
        """Test input validation for get_control tool"""
        from nist_mcp.server import get_control

        # Test with empty string
        with patch.object(
            nist_server, "get_control_details", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = ValueError("Control  not found")

            with pytest.raises(ValueError):
                await get_control("")

    @pytest.mark.asyncio
    async def test_tool_response_format(self):
        """Test that tool responses are properly formatted"""
        from nist_mcp.server import list_controls

        sample_controls = [
            {"id": "AC-1", "title": "Access Control Policy"},
            {"id": "AU-1", "title": "Audit Policy"},
        ]

        with patch.object(
            nist_server, "list_nist_controls", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = sample_controls

            result = await list_controls()

            # Validate response structure
            assert isinstance(result, list)
            for control in result:
                assert isinstance(control, dict)
                assert "id" in control
                assert "title" in control
                assert isinstance(control["id"], str)
                assert isinstance(control["title"], str)

    @pytest.mark.asyncio
    async def test_json_serialization(self):
        """Test that tool responses are JSON serializable"""
        from nist_mcp.server import list_controls, get_control

        sample_controls = [{"id": "AC-1", "title": "Test Control"}]
        sample_control = {
            "id": "AC-1",
            "title": "Test Control",
            "parts": [{"name": "statement", "prose": "Test statement"}],
        }

        with (
            patch.object(
                nist_server, "list_nist_controls", new_callable=AsyncMock
            ) as mock_list,
            patch.object(
                nist_server, "get_control_details", new_callable=AsyncMock
            ) as mock_get,
        ):
            mock_list.return_value = sample_controls
            mock_get.return_value = sample_control

            # Test list_controls serialization
            list_result = await list_controls()
            json.dumps(list_result)  # Should not raise exception

            # Test get_control serialization
            get_result = await get_control("AC-1")
            json.dumps(get_result)  # Should not raise exception


class TestMCPServerConfiguration:
    """Tests for MCP server configuration and setup"""

    def test_server_data_path_configuration(self):
        """Test server data path configuration"""
        custom_path = Path("/custom/data/path")
        server = nist_server.__class__(data_path=custom_path)
        assert server.data_path == custom_path

    def test_server_default_configuration(self):
        """Test server default configuration"""
        server = nist_server.__class__()
        assert server.data_path is not None
        assert isinstance(server.data_path, Path)

    @pytest.mark.asyncio
    async def test_server_initialization_sequence(self):
        """Test proper server initialization sequence"""
        server = nist_server.__class__()

        with patch.object(
            server.loader, "initialize", new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = None

            await server.loader.initialize()
            mock_init.assert_called_once()
