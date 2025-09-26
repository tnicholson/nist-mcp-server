#!/usr/bin/env python3
"""
NIST MCP Server - Main server implementation
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from mcp.server import FastMCP

from .data.loader import NISTDataLoader

logger = logging.getLogger(__name__)


class NISTMCPServer:
    """Main NIST MCP Server implementation"""

    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data"
        self.data_path = data_path
        self.loader = NISTDataLoader(self.data_path)
        logger.info(f"NIST MCP Server initialized with data path: {data_path}")

    async def list_nist_controls(self) -> List[Dict[str, Any]]:
        """List available NIST controls"""
        try:
            controls_data = await self.loader.load_controls()
            controls = controls_data.get("catalog", {}).get("controls", [])
            return [
                {"id": control["id"], "title": control["title"]} for control in controls
            ]
        except Exception as e:
            logger.error(f"Error loading controls: {e}")
            return []

    async def get_control_details(self, control_id: str) -> Dict[str, Any]:
        """Get details for a specific control"""
        try:
            controls_data = await self.loader.load_controls()
            control = self.loader.get_control_by_id(controls_data, control_id)
            if control:
                return control
            else:
                raise ValueError(f"Control {control_id} not found")
        except Exception as e:
            logger.error(f"Error getting control {control_id}: {e}")
            raise


nist_server = NISTMCPServer()


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    await nist_server.loader.initialize()
    yield


# Create MCP server
app = FastMCP("nist-mcp-server", lifespan=lifespan)


@app.tool()
async def list_controls() -> List[Dict[str, Any]]:
    """List all available NIST controls"""
    return await nist_server.list_nist_controls()


@app.tool()
async def get_control(control_id: str) -> Dict[str, Any]:
    """Get details for a specific NIST control"""
    return await nist_server.get_control_details(control_id)


@app.tool()
async def search_controls(
    query: str, family: Optional[str] = None, limit: int = 10
) -> Dict[str, Any]:
    """Search NIST controls by keyword or topic"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.search_controls(query, family, limit)


@app.tool()
async def get_control_family(family: str) -> Dict[str, Any]:
    """Get all controls in a specific family (e.g., 'AC', 'AU', 'CA')"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.get_control_family(family)


@app.tool()
async def get_control_mappings(control_id: str) -> Dict[str, Any]:
    """Get CSF mappings for a specific control"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.get_control_mappings(control_id)


@app.tool()
async def get_baseline_controls(baseline: str = "moderate") -> Dict[str, Any]:
    """Get controls for a specific baseline (low, moderate, high)"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.get_control_baselines(baseline)


@app.tool()
async def get_csf_framework() -> Dict[str, Any]:
    """Get the complete NIST Cybersecurity Framework structure"""
    try:
        csf_data = await nist_server.loader.load_csf()
        return csf_data
    except Exception as e:
        logger.error(f"Error loading CSF framework: {e}")
        raise


@app.tool()
async def search_csf_subcategories(
    query: str, function: Optional[str] = None
) -> Dict[str, Any]:
    """Search CSF subcategories by keyword or function"""
    try:
        csf_data = await nist_server.loader.load_csf()
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
async def csf_to_controls_mapping(subcategory_id: str) -> Dict[str, Any]:
    """Get NIST controls mapped to a specific CSF subcategory"""
    try:
        mappings_data = await nist_server.loader.load_control_mappings()

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
async def analyze_control_coverage(control_ids: List[str]) -> Dict[str, Any]:
    """Analyze coverage across control families for a list of controls"""
    try:
        controls_data = await nist_server.loader.load_controls()

        # Analyze family coverage
        family_coverage: Dict[str, int] = {}
        valid_controls = []
        invalid_controls = []

        for control_id in control_ids:
            control = nist_server.loader.get_control_by_id(controls_data, control_id)
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


@app.tool()
async def gap_analysis(
    implemented_controls: List[str], target_baseline: str = "moderate"
) -> Dict[str, Any]:
    """Perform gap analysis between implemented controls and target baseline"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.gap_analysis(implemented_controls, target_baseline)


@app.tool()
async def risk_assessment_helper(control_ids: List[str]) -> Dict[str, Any]:
    """Help assess risk coverage based on control selection"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.risk_assessment_helper(control_ids)


@app.tool()
async def compliance_mapping(framework: str, control_ids: List[str]) -> Dict[str, Any]:
    """Map controls to compliance frameworks (SOC2, ISO27001, etc.)"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.compliance_mapping(framework, control_ids)


@app.tool()
async def control_relationships(control_id: str) -> Dict[str, Any]:
    """Analyze relationships and dependencies between controls"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.control_relationships(control_id)


@app.tool()
async def validate_oscal_document(
    document: Dict[str, Any], document_type: str = "catalog"
) -> Dict[str, Any]:
    """Validate an OSCAL document against its JSON schema"""
    try:
        import jsonschema

        schemas_data = await nist_server.loader.load_oscal_schemas()
        schema = schemas_data.get("schemas", {}).get(document_type)

        if not schema:
            return {
                "valid": False,
                "error": f"Schema not found for document type: {document_type}",
                "available_types": list(schemas_data.get("schemas", {}).keys()),
            }

        try:
            jsonschema.validate(document, schema)
            return {
                "valid": True,
                "document_type": document_type,
                "message": "Document is valid according to OSCAL schema",
            }
        except jsonschema.ValidationError as e:
            return {
                "valid": False,
                "document_type": document_type,
                "error": str(e),
                "error_path": list(e.path) if e.path else [],
                "failed_value": e.instance,
            }
    except ImportError:
        return {
            "valid": False,
            "error": "jsonschema library not available for validation",
        }
    except Exception as e:
        logger.error(f"Error validating OSCAL document: {e}")
        raise


def main() -> None:
    """Entry point for the MCP server"""
    app.run()


if __name__ == "__main__":
    main()
