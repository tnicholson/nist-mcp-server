"""
Tests for NIST Data Loader
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, mock_open
import json

from nist_mcp.data.loader import NISTDataLoader


class TestNISTDataLoader:
    """Test cases for NISTDataLoader"""

    def test_loader_initialization(self):
        """Test loader initializes with data path"""
        data_path = Path("/test/data")
        loader = NISTDataLoader(data_path)
        assert loader.data_path == data_path

    @pytest.mark.asyncio
    async def test_initialize_missing_data_path(self):
        """Test initialization with missing data path"""
        data_path = Path("/nonexistent/path")
        loader = NISTDataLoader(data_path)

        with pytest.raises(FileNotFoundError):
            await loader.initialize()

    @pytest.mark.asyncio
    async def test_load_controls_from_json(self):
        """Test loading controls from JSON file"""
        data_path = Path("/test/data")
        loader = NISTDataLoader(data_path)

        sample_data = {
            "catalog": {"controls": [{"id": "AC-1", "title": "Access Control Policy"}]}
        }

        with (
            patch("aiofiles.open", mock_open(read_data=json.dumps(sample_data))),
            patch.object(Path, "exists", return_value=True),
        ):
            result = await loader.load_controls()
            assert result == sample_data
            assert loader._controls_cache == sample_data

    @pytest.mark.asyncio
    async def test_load_controls_cached(self):
        """Test loading controls returns cached data"""
        data_path = Path("/test/data")
        loader = NISTDataLoader(data_path)

        cached_data = {"catalog": {"controls": []}}
        loader._controls_cache = cached_data

        result = await loader.load_controls()
        assert result == cached_data

    def test_get_control_by_id_found(self):
        """Test finding control by ID"""
        loader = NISTDataLoader(Path("/test"))

        controls_data = {
            "catalog": {
                "controls": [
                    {"id": "AC-1", "title": "Access Control Policy"},
                    {"id": "AC-2", "title": "Account Management"},
                ]
            }
        }

        result = loader.get_control_by_id(controls_data, "AC-1")
        assert result["id"] == "AC-1"
        assert result["title"] == "Access Control Policy"

    def test_get_control_by_id_not_found(self):
        """Test control not found by ID"""
        loader = NISTDataLoader(Path("/test"))

        controls_data = {"catalog": {"controls": []}}

        result = loader.get_control_by_id(controls_data, "AC-999")
        assert result is None

    def test_search_controls_by_keyword(self):
        """Test searching controls by keyword"""
        loader = NISTDataLoader(Path("/test"))

        controls_data = {
            "catalog": {
                "controls": [
                    {
                        "id": "AC-1",
                        "title": "Access Control Policy",
                        "parts": [
                            {
                                "prose": "The organization develops access control policies"
                            }
                        ],
                    },
                    {
                        "id": "AU-1",
                        "title": "Audit Policy",
                        "parts": [
                            {"prose": "The organization develops audit policies"}
                        ],
                    },
                ]
            }
        }

        results = loader.search_controls_by_keyword(controls_data, "access", limit=10)
        assert len(results) == 1
        assert results[0]["id"] == "AC-1"

    def test_get_controls_by_family(self):
        """Test getting controls by family"""
        loader = NISTDataLoader(Path("/test"))

        controls_data = {
            "catalog": {
                "controls": [
                    {"id": "AC-1", "title": "Access Control Policy"},
                    {"id": "AC-2", "title": "Account Management"},
                    {"id": "AU-1", "title": "Audit Policy"},
                ]
            }
        }

        results = loader.get_controls_by_family(controls_data, "AC")
        assert len(results) == 2
        assert all(control["id"].startswith("AC") for control in results)
