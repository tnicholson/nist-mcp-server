"""Analysis-related MCP tool endpoints"""

import logging
from typing import Any

from mcp.server import FastMCP

from ..analysis_tools import NISTAnalysisTools

logger = logging.getLogger(__name__)


def register_analysis_endpoints(app: FastMCP, loader: Any) -> None:
    """Register all analysis-related endpoints with the MCP app"""

    analysis_tools = NISTAnalysisTools(loader)

    @app.tool()
    async def gap_analysis(
        implemented_controls: list[str], target_baseline: str = "moderate"
    ) -> dict[str, Any]:
        """Perform gap analysis between implemented controls and target baseline"""
        return await analysis_tools.gap_analysis(implemented_controls, target_baseline)

    @app.tool()
    async def risk_assessment_helper(control_ids: list[str]) -> dict[str, Any]:
        """Help assess risk coverage based on control selection"""
        return await analysis_tools.risk_assessment_helper(control_ids)

    @app.tool()
    async def compliance_mapping(framework: str, control_ids: list[str]) -> dict[str, Any]:
        """Map controls to compliance frameworks (SOC2, ISO27001, etc.)"""
        return await analysis_tools.compliance_mapping(framework, control_ids)

    @app.tool()
    async def control_relationships(control_id: str) -> dict[str, Any]:
        """Analyze relationships and dependencies between controls"""
        return await analysis_tools.control_relationships(control_id)
