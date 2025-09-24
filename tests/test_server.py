"""
Basic tests for NIST MCP Server
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from nist_mcp.server import NISTMCPServer


class TestNISTMCPServer:
    """Test cases for NISTMCPServer"""

    def test_server_initialization(self):
        """Test server initializes with default data path"""
        server = NISTMCPServer()
        assert server.data_path is not None
        assert isinstance(server.data_path, Path)

    def test_server_initialization_custom_path(self):
        """Test server initializes with custom data path"""
        custom_path = Path("/custom/data/path")
        server = NISTMCPServer(data_path=custom_path)
        assert server.data_path == custom_path

    @pytest.mark.asyncio
    async def test_list_nist_controls_empty(self):
        """Test listing controls when no data is available"""
        server = NISTMCPServer()

        # Mock the loader to return empty data
        with patch.object(
            server.loader, "load_controls", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = {"catalog": {"controls": []}}

            result = await server.list_nist_controls()
            assert result == []
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_nist_controls_with_data(self):
        """Test listing controls with sample data"""
        server = NISTMCPServer()

        sample_controls = [
            {"id": "AC-1", "title": "Access Control Policy and Procedures"},
            {"id": "AC-2", "title": "Account Management"},
        ]

        with patch.object(
            server.loader, "load_controls", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = {"catalog": {"controls": sample_controls}}

            result = await server.list_nist_controls()

            expected = [
                {"id": "AC-1", "title": "Access Control Policy and Procedures"},
                {"id": "AC-2", "title": "Account Management"},
            ]
            assert result == expected
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_control_details_found(self):
        """Test getting control details for existing control"""
        server = NISTMCPServer()

        sample_control = {
            "id": "AC-1",
            "title": "Access Control Policy and Procedures",
            "class": "SP800-53",
        }

        with (
            patch.object(
                server.loader, "load_controls", new_callable=AsyncMock
            ) as mock_load,
            patch.object(server.loader, "get_control_by_id") as mock_get,
        ):
            mock_load.return_value = {"catalog": {"controls": [sample_control]}}
            mock_get.return_value = sample_control

            result = await server.get_control_details("AC-1")
            assert result == sample_control
            mock_load.assert_called_once()
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_control_details_not_found(self):
        """Test getting control details for non-existent control"""
        server = NISTMCPServer()

        with (
            patch.object(
                server.loader, "load_controls", new_callable=AsyncMock
            ) as mock_load,
            patch.object(server.loader, "get_control_by_id") as mock_get,
        ):
            mock_load.return_value = {"catalog": {"controls": []}}
            mock_get.return_value = None

            with pytest.raises(ValueError, match="Control AC-999 not found"):
                await server.get_control_details("AC-999")
