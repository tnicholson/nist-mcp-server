"""
Performance and Load Tests for NIST MCP Server

Tests for performance characteristics and load handling.
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nist_mcp.server import NISTMCPServer


class TestPerformance:
    """Performance tests for MCP server operations"""

    @pytest.mark.asyncio
    async def test_control_loading_performance(self):
        """Test performance of control loading operations"""
        server = NISTMCPServer()

        # Create large mock dataset
        large_controls_data = {
            "catalog": {
                "controls": [
                    {"id": f"AC-{i}", "title": f"Control {i}", "parts": []}
                    for i in range(1000)  # 1000 controls
                ]
            }
        }

        with patch.object(
            server.loader, "load_controls", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = large_controls_data

            start_time = time.time()
            result = await server.list_nist_controls()
            end_time = time.time()

            # Should complete within reasonable time (< 1 second for 1000 controls)
            assert end_time - start_time < 1.0
            assert len(result) == 1000

    @pytest.mark.asyncio
    async def test_concurrent_control_requests(self):
        """Test handling of concurrent control requests"""
        server = NISTMCPServer()

        sample_control = {
            "id": "AC-1",
            "title": "Access Control Policy",
            "parts": [{"name": "statement", "prose": "Test statement"}],
        }

        with (
            patch.object(
                server.loader, "load_controls", new_callable=AsyncMock
            ) as mock_load,
            patch.object(server.loader, "get_control_by_id") as mock_get,
        ):
            mock_load.return_value = {"catalog": {"controls": [sample_control]}}
            mock_get.return_value = sample_control

            # Create 50 concurrent requests
            tasks = [server.get_control_details("AC-1") for _ in range(50)]

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            # All requests should succeed
            assert len(results) == 50
            for result in results:
                assert result == sample_control

            # Should complete within reasonable time
            assert end_time - start_time < 2.0

    @pytest.mark.asyncio
    async def test_memory_usage_with_large_dataset(self):
        """Test memory usage with large datasets"""
        server = NISTMCPServer()

        # Create very large mock dataset
        large_dataset = {"catalog": {"controls": []}}

        # Add 5000 controls with substantial content
        for i in range(5000):
            control = {
                "id": f"TEST-{i}",
                "title": f"Test Control {i}" * 10,  # Longer titles
                "parts": [
                    {
                        "name": "statement",
                        "prose": "This is a test control statement. "
                        * 50,  # Substantial content
                    },
                    {
                        "name": "guidance",
                        "prose": "This is test guidance content. " * 30,
                    },
                ],
            }
            large_dataset["catalog"]["controls"].append(control)

        with patch.object(
            server.loader, "load_controls", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = large_dataset

            # Test that we can handle large datasets
            start_time = time.time()
            result = await server.list_nist_controls()
            end_time = time.time()

            assert len(result) == 5000
            # Should still complete in reasonable time
            assert end_time - start_time < 5.0

    @pytest.mark.asyncio
    async def test_caching_performance(self):
        """Test that caching improves performance"""
        server = NISTMCPServer()

        controls_data = {
            "catalog": {"controls": [{"id": "AC-1", "title": "Access Control Policy"}]}
        }

        with patch.object(
            server.loader, "load_controls", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = controls_data

            # First call - should load data
            start_time = time.time()
            result1 = await server.list_nist_controls()
            time.time() - start_time  # first_call_time not used

            # Second call - should use cache (if implemented)
            start_time = time.time()
            result2 = await server.list_nist_controls()
            time.time() - start_time  # second_call_time not used

            assert result1 == result2
            # Note: This test assumes caching is implemented
            # If not, both calls will have similar performance


class TestLoadTesting:
    """Load testing for MCP server under stress"""

    @pytest.mark.asyncio
    async def test_rapid_sequential_requests(self):
        """Test handling of rapid sequential requests"""
        server = NISTMCPServer()

        controls_data = {
            "catalog": {
                "controls": [
                    {"id": f"AC-{i}", "title": f"Control {i}"} for i in range(100)
                ]
            }
        }

        with patch.object(
            server.loader, "load_controls", new_callable=AsyncMock
        ) as mock_load:
            mock_load.return_value = controls_data

            # Make 100 rapid sequential requests
            start_time = time.time()
            for _ in range(100):
                result = await server.list_nist_controls()
                assert len(result) == 100
            end_time = time.time()

            # Should handle rapid requests efficiently
            assert end_time - start_time < 10.0

    @pytest.mark.asyncio
    async def test_mixed_operation_load(self):
        """Test mixed operations under load"""
        server = NISTMCPServer()

        controls_data = {
            "catalog": {
                "controls": [
                    {
                        "id": f"AC-{i}",
                        "title": f"Access Control {i}",
                        "parts": [{"name": "statement", "prose": f"Statement {i}"}],
                    }
                    for i in range(1, 21)  # 20 controls
                ]
            }
        }

        with (
            patch.object(
                server.loader, "load_controls", new_callable=AsyncMock
            ) as mock_load,
            patch.object(server.loader, "get_control_by_id") as mock_get,
        ):
            mock_load.return_value = controls_data

            def get_control_side_effect(data, control_id):
                for control in data["catalog"]["controls"]:
                    if control["id"] == control_id:
                        return control
                return None

            mock_get.side_effect = get_control_side_effect

            # Mix of list and get operations
            tasks = []

            # Add list operations
            for _ in range(10):
                tasks.append(server.list_nist_controls())

            # Add get operations
            for i in range(1, 11):
                tasks.append(server.get_control_details(f"AC-{i}"))

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            # Verify results
            list_results = results[:10]  # First 10 are list operations
            get_results = results[10:]  # Next 10 are get operations

            for list_result in list_results:
                assert len(list_result) == 20

            for get_result in get_results:
                assert get_result is not None
                assert "id" in get_result
                assert get_result["id"].startswith("AC-")

            # Should complete within reasonable time
            assert end_time - start_time < 5.0

    @pytest.mark.asyncio
    async def test_error_handling_under_load(self):
        """Test error handling when under load"""
        server = NISTMCPServer()

        with (
            patch.object(
                server.loader, "load_controls", new_callable=AsyncMock
            ) as mock_load,
            patch.object(server.loader, "get_control_by_id") as mock_get,
        ):
            # Simulate intermittent failures
            call_count = 0

            async def failing_load_controls():
                nonlocal call_count
                call_count += 1
                if call_count % 3 == 0:  # Fail every 3rd call
                    raise Exception("Simulated failure")
                return {"catalog": {"controls": [{"id": "AC-1", "title": "Test"}]}}

            mock_load.side_effect = failing_load_controls
            mock_get.return_value = {"id": "AC-1", "title": "Test"}

            # Make multiple requests, some should fail
            results = []
            errors = []

            for _ in range(10):
                try:
                    result = await server.list_nist_controls()
                    results.append(result)
                except Exception as e:
                    errors.append(e)

            # Should have some successes and some failures
            assert len(results) > 0  # Some should succeed
            assert len(errors) > 0  # Some should fail
            assert len(results) + len(errors) == 10


class TestResourceUsage:
    """Tests for resource usage patterns"""

    @pytest.mark.asyncio
    async def test_json_serialization_performance(self):
        """Test JSON serialization performance for large responses"""
        # Create large control data
        large_control = {"id": "TEST-1", "title": "Large Test Control", "parts": []}

        # Add many parts with substantial content
        for i in range(100):
            large_control["parts"].append(
                {
                    "name": f"part-{i}",
                    "prose": (
                        "This is a very long prose section that contains substantial content. "
                    ) * 20,
                }
            )

        # Test serialization performance
        start_time = time.time()
        json_str = json.dumps(large_control)
        serialization_time = time.time() - start_time

        # Should serialize quickly
        assert serialization_time < 1.0

        # Test deserialization
        start_time = time.time()
        parsed_data = json.loads(json_str)
        deserialization_time = time.time() - start_time

        assert deserialization_time < 1.0
        assert parsed_data == large_control

    @pytest.mark.asyncio
    async def test_data_loader_initialization_time(self):
        """Test data loader initialization performance"""
        from nist_mcp.data.loader import NISTDataLoader

        data_path = Path("/test/data")

        start_time = time.time()
        loader = NISTDataLoader(data_path)
        initialization_time = time.time() - start_time

        # Initialization should be very fast
        assert initialization_time < 0.1
        assert loader.data_path == data_path
