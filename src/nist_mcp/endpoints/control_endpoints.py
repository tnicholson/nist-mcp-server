"""Control-related MCP tool endpoints"""

import logging
from typing import Any

from mcp.server import FastMCP

from ..control_tools import ControlTools

logger = logging.getLogger(__name__)


def register_control_endpoints(app: FastMCP, loader: Any) -> None:
    """Register all control-related endpoints with the MCP app"""

    control_tools = ControlTools(loader)

    @app.tool()
    async def list_controls() -> list[dict[str, Any]]:
        """List all available NIST controls"""
        try:
            controls_data = await loader.load_controls()
            controls = controls_data.get("catalog", {}).get("controls", [])
            return [
                {"id": control["id"], "title": control["title"]} for control in controls
            ]
        except Exception as e:
            logger.error(f"Error loading controls: {e}")
            return []

    @app.tool()
    async def get_control(control_id: str) -> dict[str, Any]:
        """Get details for a specific NIST control"""
        return await control_tools.get_control(control_id)

    @app.tool()
    async def search_controls(
        query: str, family: str | None = None, limit: int = 10
    ) -> dict[str, Any]:
        """Search NIST controls by keyword or topic"""
        return await control_tools.search_controls(query, family, limit)

    @app.tool()
    async def get_control_family(family: str) -> dict[str, Any]:
        """Get all controls in a specific family (e.g., 'AC', 'AU', 'CA')"""
        return await control_tools.get_control_family(family)

    @app.tool()
    async def get_control_mappings(control_id: str) -> dict[str, Any]:
        """Get CSF mappings for a specific control"""
        return await control_tools.get_control_mappings(control_id)

    @app.tool()
    async def get_baseline_controls(baseline: str = "moderate") -> dict[str, Any]:
        """Get controls for a specific baseline (low, moderate, high)"""
        return await control_tools.get_control_baselines(baseline)

    @app.tool()
    async def get_csf_framework() -> dict[str, Any]:
        """Get the complete NIST Cybersecurity Framework structure"""
        try:
            csf_data = await loader.load_csf()
            return csf_data
        except Exception as e:
            logger.error(f"Error loading CSF framework: {e}")
            raise

    @app.tool()
    async def search_csf_subcategories(
        query: str, function: str | None = None
    ) -> dict[str, Any]:
        """Search CSF subcategories by keyword or function"""
        try:
            csf_data = await loader.load_csf()
            functions = csf_data.get("framework", {}).get("functions", [])

            matches = []
            query_lower = query.lower()

            for func in functions:
                if function and func.get("id", "").lower() != function.lower():
                    continue

                for category in func.get("categories", []):
                    for subcategory in category.get("subcategories", []):
                        subcat_text = f"{subcategory.get('id', '')} {subcategory.get('description', '')}".lower()
                        if query_lower in subcat_text:
                            matches.append(
                                {
                                    "id": subcategory.get("id", ""),
                                    "description": subcategory.get("description", ""),
                                    "function": func.get("id", ""),
                                    "function_name": func.get("name", ""),
                                    "category": category.get("id", ""),
                                    "category_name": category.get("name", ""),
                                }
                            )

            return {
                "query": query,
                "function_filter": function,
                "total_matches": len(matches),
                "subcategories": matches[:20],  # Limit results
            }
        except Exception as e:
            logger.error(f"Error searching CSF subcategories: {e}")
            raise

    @app.tool()
    async def csf_to_controls_mapping(subcategory_id: str) -> dict[str, Any]:
        """Get NIST controls mapped to a specific CSF subcategory"""
        try:
            mappings_data = await loader.load_control_mappings()

            # Reverse lookup - find controls that map to this subcategory
            mapped_controls = []
            for control_id, csf_mappings in mappings_data.get("mappings", {}).items():
                if subcategory_id in csf_mappings:
                    mapped_controls.append(control_id)

            return {
                "subcategory_id": subcategory_id,
                "mapped_controls": mapped_controls,
                "total_controls": len(mapped_controls),
            }
        except Exception as e:
            logger.error(f"Error mapping CSF to controls: {e}")
            raise

    @app.tool()
    async def analyze_control_coverage(control_ids: list[str]) -> dict[str, Any]:
        """Analyze coverage across control families for a list of controls"""
        try:
            controls_data = await loader.load_controls()

            # Analyze family coverage
            family_coverage: dict[str, int] = {}
            valid_controls = []
            invalid_controls = []

            for control_id in control_ids:
                control = loader.get_control_by_id(controls_data, control_id)
                if control:
                    valid_controls.append(control_id)
                    family = control_id[:2]
                    family_coverage[family] = family_coverage.get(family, 0) + 1
                else:
                    invalid_controls.append(control_id)

            return {
                "total_controls": len(control_ids),
                "valid_controls": len(valid_controls),
                "invalid_controls": invalid_controls,
                "family_coverage": family_coverage,
                "families_covered": len(family_coverage),
                "coverage_analysis": {
                    family: {
                        "count": count,
                        "percentage": round((count / len(valid_controls)) * 100, 2),
                    }
                    for family, count in family_coverage.items()
                },
            }
        except Exception as e:
            logger.error(f"Error analyzing control coverage: {e}")
            raise
