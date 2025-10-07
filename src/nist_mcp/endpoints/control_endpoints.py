"""Control-related MCP tool endpoints"""

import logging
from typing import Any

from mcp.server import FastMCP

from ..infrastructure.container import get_container

logger = logging.getLogger(__name__)


async def register_control_endpoints(app: FastMCP, loader: Any) -> None:
    """Register all control-related endpoints with the MCP app"""

    # Get the control service from the container
    container = get_container()
    control_service = await container.get_control_service()

    @app.tool()
    async def list_controls() -> list[dict[str, Any]]:
        """List all available NIST controls"""
        return await control_service.list_controls()

    @app.tool()
    async def get_control(control_id: str) -> dict[str, Any]:
        """Get details for a specific NIST control"""
        return await control_service.get_control(control_id)

    @app.tool()
    async def search_controls(
        query: str, family: str | None = None, limit: int = 10
    ) -> dict[str, Any]:
        """Search NIST controls by keyword or topic"""
        return await control_service.search_controls(query, family, limit)

    @app.tool()
    async def get_control_family(family: str) -> dict[str, Any]:
        """Get all controls in a specific family (e.g., 'AC', 'AU', 'CA')"""
        return await control_service.get_control_family(family)

    @app.tool()
    async def get_control_mappings(control_id: str) -> dict[str, Any]:
        """Get CSF mappings for a specific control"""
        return await control_service.get_control_mappings(control_id)

    @app.tool()
    async def get_baseline_controls(baseline: str = "moderate") -> dict[str, Any]:
        """Get controls for a specific baseline (low, moderate, high)"""
        return await control_service.get_baselines(baseline)

    @app.tool()
    async def get_csf_framework() -> dict[str, Any]:
        """Get the complete NIST Cybersecurity Framework structure"""
        return await control_service.get_csf_framework()

    @app.tool()
    async def search_csf_subcategories(
        query: str, function: str | None = None
    ) -> dict[str, Any]:
        """Search CSF subcategories by keyword or function"""
        return await control_service.search_csf_subcategories(query, function)

    @app.tool()
    async def csf_to_controls_mapping(subcategory_id: str) -> dict[str, Any]:
        """Get NIST controls mapped to a specific CSF subcategory"""
        return await control_service.map_csf_to_controls(subcategory_id)

    @app.tool()
    async def analyze_control_coverage(control_ids: list[str]) -> dict[str, Any]:
        """Analyze coverage across control families for a list of controls"""
        return await control_service.analyze_control_coverage(control_ids)
