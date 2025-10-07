#!/usr/bin/env python3
"""NIST MCP Server - Main server implementation"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime

from mcp.server import FastMCP

from .data.loader import NISTDataLoader
from .history.storage import HistoricalStorage
from .monitoring.monitor import ControlMonitor
from .workflows.strands import StrandsOrchestrator, create_compliance_assessment_strand
from .connectors.base import connector_registry
from .connectors.aws import AWSConnector

logger = logging.getLogger(__name__)


class NISTMCPServer:
    """Main NIST MCP Server implementation"""

    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data"
        self.data_path = data_path
        self.loader = NISTDataLoader(self.data_path)
        logger.info(f"NIST MCP Server initialized with data path: {data_path}")

    async def list_nist_controls(self) -> list[dict[str, Any]]:
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

    async def get_control_details(self, control_id: str) -> dict[str, Any]:
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
async def list_controls() -> list[dict[str, Any]]:
    """List all available NIST controls"""
    return await nist_server.list_nist_controls()


@app.tool()
async def get_control(control_id: str) -> dict[str, Any]:
    """Get details for a specific NIST control"""
    return await nist_server.get_control_details(control_id)


@app.tool()
async def search_controls(
    query: str, family: str | None = None, limit: int = 10
) -> dict[str, Any]:
    """Search NIST controls by keyword or topic"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.search_controls(query, family, limit)


@app.tool()
async def get_control_family(family: str) -> dict[str, Any]:
    """Get all controls in a specific family (e.g., 'AC', 'AU', 'CA')"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.get_control_family(family)


@app.tool()
async def get_control_mappings(control_id: str) -> dict[str, Any]:
    """Get CSF mappings for a specific control"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.get_control_mappings(control_id)


@app.tool()
async def get_baseline_controls(baseline: str = "moderate") -> dict[str, Any]:
    """Get controls for a specific baseline (low, moderate, high)"""
    from .control_tools import ControlTools

    tools = ControlTools(nist_server.loader)
    return await tools.get_control_baselines(baseline)


@app.tool()
async def get_csf_framework() -> dict[str, Any]:
    """Get the complete NIST Cybersecurity Framework structure"""
    try:
        csf_data = await nist_server.loader.load_csf()
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
async def csf_to_controls_mapping(subcategory_id: str) -> dict[str, Any]:
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
async def analyze_control_coverage(control_ids: list[str]) -> dict[str, Any]:
    """Analyze coverage across control families for a list of controls"""
    try:
        controls_data = await nist_server.loader.load_controls()

        # Analyze family coverage
        family_coverage: dict[str, int] = {}
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
    implemented_controls: list[str], target_baseline: str = "moderate"
) -> dict[str, Any]:
    """Perform gap analysis between implemented controls and target baseline"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.gap_analysis(implemented_controls, target_baseline)


@app.tool()
async def risk_assessment_helper(control_ids: list[str]) -> dict[str, Any]:
    """Help assess risk coverage based on control selection"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.risk_assessment_helper(control_ids)


@app.tool()
async def compliance_mapping(framework: str, control_ids: list[str]) -> dict[str, Any]:
    """Map controls to compliance frameworks (SOC2, ISO27001, etc.)"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.compliance_mapping(framework, control_ids)


@app.tool()
async def control_relationships(control_id: str) -> dict[str, Any]:
    """Analyze relationships and dependencies between controls"""
    from .analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(nist_server.loader)
    return await analysis.control_relationships(control_id)


@app.tool()
async def get_sp800171_baseline() -> dict[str, Any]:
    """Get NIST SP 800-171 CUI baseline controls"""
    try:
        baseline_data = await nist_server.loader.load_sp800171_baseline()

        # Extract control IDs from OSCAL profile format
        control_ids = []
        imports = baseline_data.get("profile", {}).get("imports", [])
        if imports:
            include_controls = imports[0].get("include-controls", [])
            if include_controls:
                with_ids = include_controls[0].get("with-ids", [])
                control_ids = [control_id for control_id in with_ids if isinstance(control_id, str)]

        controls_data = await nist_server.loader.load_controls()

        # Get control details for baseline controls
        baseline_controls = []
        found_control_ids = set()

        for group in controls_data.get("catalog", {}).get("groups", []):
            for control in group.get("controls", []):
                control_id = control.get("id", "").upper()
                if control_id in [cid.upper() for cid in control_ids]:
                    baseline_controls.append({
                        "id": control_id,
                        "title": control.get("title", ""),
                        "family": control_id[:2],
                        "class": "SP800-171"
                    })
                    found_control_ids.add(control_id)

        return {
            "baseline": "SP 800-171 CUI",
            "total_controls": len(baseline_controls),
            "controls": baseline_controls,
            "description": "Controls required to protect Controlled Unclassified Information (CUI)",
        }
    except Exception as e:
        logger.error(f"Error loading SP 800-171 baseline: {e}")
        raise


@app.tool()
async def get_sp800171_catalog() -> dict[str, Any]:
    """Get the complete NIST SP 800-171 catalog with all 110 security requirements"""
    try:
        catalog_data = await nist_server.loader.load_sp800171_catalog()

        groups = catalog_data.get("catalog", {}).get("groups", [])
        total_controls = sum(len(group.get("controls", [])) for group in groups)

        return {
            "catalog": "NIST SP 800-171 Rev 2",
            "version": "2.0",
            "total_controls": total_controls,
            "families": len(groups),
            "groups": [{"id": group["id"], "title": group["title"], "controls_count": len(group.get("controls", []))} for group in groups],
            "description": "Complete catalog of 110 security requirements for protecting Controlled Unclassified Information (CUI)"
        }
    except Exception as e:
        logger.error(f"Error loading SP 800-171 catalog: {e}")
        raise


@app.tool()
async def get_sp800171_control(control_id: str) -> dict[str, Any]:
    """Get details for a specific SP 800-171 control"""
    try:
        catalog_data = await nist_server.loader.load_sp800171_catalog()
        control_id = control_id.upper()

        # Search through groups for the control
        for group in catalog_data.get("catalog", {}).get("groups", []):
            for control in group.get("controls", []):
                if control.get("id", "").upper() == control_id:
                    # Get SP 800-53 mappings
                    sp80053_mappings = control.get("sp800-53-mappings", [])

                    return {
                        "id": control["id"],
                        "family": group["id"],
                        "family_name": group["title"],
                        "title": control["title"],
                        "description": control["title"],
                        "sp800_53_mappings": sp80053_mappings,
                        "class": "SP800-171"
                    }

        raise ValueError(f"SP 800-171 control {control_id} not found")
    except Exception as e:
        logger.error(f"Error getting SP 800-171 control {control_id}: {e}")
        raise


@app.tool()
async def get_sp800171_family(family: str) -> dict[str, Any]:
    """Get all SP 800-171 controls in a specific family"""
    try:
        catalog_data = await nist_server.loader.load_sp800171_catalog()
        family = family.upper()

        for group in catalog_data.get("catalog", {}).get("groups", []):
            if group["id"] == family:
                controls = []
                for control in group.get("controls", []):
                    controls.append({
                        "id": control["id"],
                        "title": control["title"],
                        "sp800_53_mappings": control.get("sp800-53-mappings", [])
                    })

                return {
                    "family": family,
                    "family_name": group["title"],
                    "total_controls": len(controls),
                    "controls": controls,
                    "description": group["description"]
                }

        raise ValueError(f"SP 800-171 family {family} not found")
    except Exception as e:
        logger.error(f"Error getting SP 800-171 family {family}: {e}")
        raise


@app.tool()
async def sp800171_to_sp80053_mapping(control_ids: list[str]) -> dict[str, Any]:
    """Map SP 800-171 requirements to their corresponding SP 800-53 controls"""
    try:
        catalog_data = await nist_server.loader.load_sp800171_catalog()
        sp80053_mappings = {}

        for control_id in control_ids:
            control_id = control_id.upper()
            sp80053_mappings[control_id] = []

            # Find the control in the catalog
            for group in catalog_data.get("catalog", {}).get("groups", []):
                for control in group.get("controls", []):
                    if control.get("id", "").upper() == control_id:
                        sp80053_mappings[control_id] = control.get("sp800-53-mappings", [])
                        break
                if sp80053_mappings[control_id]:
                    break

        return {
            "sp800171_to_sp80053_mappings": sp80053_mappings,
            "total_sp800171_controls": len(control_ids),
            "controls_mapped": len([k for k, v in sp80053_mappings.items() if v])
        }
    except Exception as e:
        logger.error(f"Error mapping SP 800-171 to SP 800-53: {e}")
        raise


@app.tool()
async def get_cmmc_framework() -> dict[str, Any]:
    """Get the complete CMMC framework structure"""
    try:
        cmmc_data = await nist_server.loader.load_cmmc_framework()
        return cmmc_data
    except Exception as e:
        logger.error(f"Error loading CMMC framework: {e}")
        raise


@app.tool()
async def get_cmmc_level(level: int) -> dict[str, Any]:
    """Get controls for a specific CMMC level"""
    if level not in [1, 2, 3, 4, 5]:
        raise ValueError("CMMC level must be between 1 and 5")

    try:
        cmmc_data = await nist_server.loader.load_cmmc_framework()

        level_data = None
        for lvl in cmmc_data.get("framework", {}).get("levels", []):
            if lvl.get("level") == level:
                level_data = lvl
                break

        if not level_data:
            raise ValueError(f"CMMC Level {level} not found")

        controls_data = await nist_server.loader.load_controls()

        # Get control details for level controls
        level_controls = []
        found_control_ids = set()

        # Search through all controls in catalog
        for group in controls_data.get("catalog", {}).get("groups", []):
            for control in group.get("controls", []):
                control_id = control.get("id", "").upper()
                if control_id in [cid.upper() for cid in level_data.get("controls", [])]:
                    level_controls.append({
                        "id": control_id,
                        "title": control.get("title", ""),
                        "family": control_id[:2],
                        "class": "CMMC"
                    })
                    found_control_ids.add(control_id)

        level_data["resolved_controls"] = level_controls

        return level_data
    except Exception as e:
        logger.error(f"Error loading CMMC level {level}: {e}")
        raise


@app.tool()
async def cmmc_compliance_assessment(
    implemented_controls: list[str], target_level: int = 2
) -> dict[str, Any]:
    """Perform CMMC compliance assessment for implemented controls against a target level"""
    if target_level not in [1, 2, 3, 4, 5]:
        raise ValueError("CMMC target level must be between 1 and 5")

    try:
        cmmc_data = await nist_server.loader.load_cmmc_framework()

        # Get required controls for all levels up to target level
        required_controls = set()
        required_by_level = {}

        for i in range(1, target_level + 1):
            for lvl in cmmc_data.get("framework", {}).get("levels", []):
                if lvl.get("level") == i:
                    level_controls = [cid.upper() for cid in lvl.get("controls", [])]
                    required_controls.update(level_controls)
                    required_by_level[f"Level {i}"] = level_controls
                    break

        implemented_controls_upper = [cid.upper() for cid in implemented_controls]

        # Assess compliance
        compliant_controls = []
        missing_controls = []
        level_compliance = {}

        for level_name, level_controls in required_by_level.items():
            implemented_for_level = [cid for cid in implemented_controls_upper if cid in level_controls]
            missing_for_level = [cid for cid in level_controls if cid not in implemented_controls_upper]

            level_compliance[level_name] = {
                "required": len(level_controls),
                "implemented": len(implemented_for_level),
                "missing": len(missing_for_level),
                "compliance_percentage": round((len(implemented_for_level) / len(level_controls)) * 100, 2),
                "missing_controls": missing_for_level
            }

        # Overall assessment
        total_required = len(required_controls)
        total_implemented = len([cid for cid in implemented_controls_upper if cid in required_controls])

        # Check if all controls for target level are implemented
        target_level_controls = required_by_level.get(f"Level {target_level}", [])
        has_target_level = all(cid in implemented_controls_upper for cid in target_level_controls)

        assessment_level = target_level if has_target_level else target_level - 1

        return {
            "assessment": {
                "implemented_controls_count": len(implemented_controls),
                "target_level": target_level,
                "assessment_level": assessment_level,
                "overall_compliance_percentage": round((total_implemented / total_required) * 100, 2),
                "fully_compliant_to_target": has_target_level,
                "total_required": total_required,
                "total_implemented": total_implemented,
                "total_missing": total_required - total_implemented
            },
            "level_details": level_compliance,
            "recommendations": [
                f"Achieve Level {target_level}" if has_target_level else f"Work towards Level {target_level}",
                f"Implement missing {total_required - total_implemented} controls across all levels"
            ]
        }
    except Exception as e:
        logger.error(f"Error performing CMMC compliance assessment: {e}")
        raise


@app.tool()
async def get_fedramp_framework() -> dict[str, Any]:
    """Get the complete FedRAMP framework structure"""
    try:
        fedramp_data = await nist_server.loader.load_fedramp_framework()
        return fedramp_data
    except Exception as e:
        logger.error(f"Error loading FedRAMP framework: {e}")
        raise


@app.tool()
async def get_fedramp_baseline(impact_level: str) -> dict[str, Any]:
    """Get FedRAMP controls for a specific impact level (low, moderate, high)"""
    impact_level = impact_level.lower()
    if impact_level not in ["low", "moderate", "high"]:
        raise ValueError("Impact level must be 'low', 'moderate', or 'high'")

    try:
        fedramp_data = await nist_server.loader.load_fedramp_framework()

        # Find the matching baseline
        target_baseline = None
        for baseline in fedramp_data.get("framework", {}).get("baselines", []):
            if baseline.get("level", "").lower() == impact_level:
                target_baseline = baseline
                break

        if not target_baseline:
            raise ValueError(f"FedRAMP baseline not found for impact level: {impact_level}")

        # Load the corresponding SP 800-53 baseline profile
        if impact_level == "low":
            baseline_data = await nist_server.loader.load_baseline_profiles()
            baseline_profile = baseline_data.get("low", {})
        elif impact_level == "moderate":
            baseline_data = await nist_server.loader.load_baseline_profiles()
            baseline_profile = baseline_data.get("moderate", {})
        else:  # high
            baseline_data = await nist_server.loader.load_baseline_profiles()
            baseline_profile = baseline_data.get("high", {})

        # Extract control IDs from OSCAL profile format
        control_ids = []
        if baseline_profile:
            imports = baseline_profile.get("profile", {}).get("imports", [])
            if imports:
                include_controls = imports[0].get("include-controls", [])
                if include_controls:
                    with_ids = include_controls[0].get("with-ids", [])
                    control_ids = [control_id for control_id in with_ids if isinstance(control_id, str)]

        controls_data = await nist_server.loader.load_controls()

        # Get control details for baseline controls
        baseline_controls = []
        found_control_ids = set()

        for group in controls_data.get("catalog", {}).get("groups", []):
            for control in group.get("controls", []):
                control_id = control.get("id", "").upper()
                if control_id in [cid.upper() for cid in control_ids]:
                    baseline_controls.append({
                        "id": control_id,
                        "title": control.get("title", ""),
                        "family": control_id[:2],
                        "class": "FedRAMP"
                    })
                    found_control_ids.add(control_id)

        return {
            "baseline": f"FedRAMP {impact_level.title()} Impact",
            "impact_level": target_baseline.get("impact_level", ""),
            "description": target_baseline.get("description", ""),
            "total_controls": len(baseline_controls),
            "controls": baseline_controls,
        }
    except Exception as e:
        logger.error(f"Error loading FedRAMP baseline {impact_level}: {e}")
        raise


@app.tool()
async def fedramp_readiness_assessment(
    implemented_controls: list[str], service_model: str = "saas"
) -> dict[str, Any]:
    """Perform FedRAMP readiness assessment for cloud service providers"""
    service_model = service_model.lower()
    if service_model not in ["saas", "paas", "iaas"]:
        raise ValueError("Service model must be 'saas', 'paas', or 'iaas'")

    try:
        fedramp_data = await nist_server.loader.load_fedramp_framework()

        # For simplicity, we'll use the moderate baseline as the primary assessment
        # In practice, this would be more sophisticated based on the service model
        baseline_data = await nist_server.loader.load_baseline_profiles()
        moderate_profile = baseline_data.get("moderate", {})

        # Extract required control IDs from OSCAL profile
        required_control_ids = set()
        if moderate_profile:
            imports = moderate_profile.get("profile", {}).get("imports", [])
            if imports:
                include_controls = imports[0].get("include-controls", [])
                if include_controls:
                    with_ids = include_controls[0].get("with-ids", [])
                    required_control_ids = set(with_ids)

        implemented_controls_upper = [cid.upper() for cid in implemented_controls]

        # Assess implementation
        implemented_count = len([cid for cid in implemented_controls_upper if cid in required_control_ids])
        total_required = len(required_control_ids)
        missing_count = total_required - implemented_count

        compliance_percentage = round((implemented_count / total_required) * 100, 2)

        # Determine readiness level
        if compliance_percentage >= 95:
            readiness = "Ready for Authorization"
            pathways = ["Priority", "General (JAB)", "Agency"]
        elif compliance_percentage >= 85:
            readiness = "High Readiness"
            pathways = ["General (JAB)", "Agency"]
        elif compliance_percentage >= 75:
            readiness = "Medium Readiness"
            pathways = ["Agency"]
        else:
            readiness = "Low Readiness"
            pathways = ["Not yet ready for authorization"]

        return {
            "assessment": {
                "service_model": service_model.upper(),
                "target_baseline": "Moderate Impact",
                "current_compliance_percentage": f"{compliance_percentage}%",
                "implemented_controls": implemented_count,
                "total_required_controls": total_required,
                "missing_controls": missing_count,
                "readiness_level": readiness,
                "available_pathways": pathways
            },
            "fedramp_requirements": fedramp_data.get("framework", {}).get("requirements", {}),
            "recommendations": [
                f"Achieve at least 75% compliance before pursuing authorization (currently {compliance_percentage}%)",
                f"Focus on implementing missing {missing_count} controls",
                f"For {service_model.upper()} services, consider the guidance in FedRAMP Rev 4",
                "Develop comprehensive System Security Plan (SSP)",
                "Prepare for continuous monitoring requirements"
            ]
        }
    except Exception as e:
        logger.error(f"Error performing FedRAMP readiness assessment: {e}")
        raise


@app.tool()
async def validate_oscal_document(
    document: dict[str, Any], document_type: str = "catalog"
) -> dict[str, Any]:
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


# Advanced MCP Tools for Enhanced Features

# Initialize components
_storage = HistoricalStorage()
_monitor = ControlMonitor(_storage)
_orchestrator = StrandsOrchestrator(_storage, _monitor)

# Register connector types
connector_registry.register_connector_type("aws", AWSConnector)


async def _ensure_initialized():
    """Ensure components are initialized"""
    await _storage.initialize()
    await _orchestrator.orchestrator.storage.initialize()  # type: ignore


@app.tool()
async def start_continuous_monitoring(
    control_id: str,
    check_interval_hours: int = 24,
    connector_id: Optional[str] = None
) -> dict[str, Any]:
    """Start continuous monitoring for a specific control"""
    await _ensure_initialized()

    monitor_id = _monitor.start_monitoring_control(
        control_id=control_id,
        check_interval_hours=check_interval_hours,
        connector_id=connector_id,
        check_type="continuous"
    )

    return {
        "monitor_id": monitor_id,
        "control_id": control_id,
        "interval_hours": check_interval_hours,
        "status": "started",
        "message": f"Continuous monitoring started for control {control_id}"
    }


@app.tool()
async def stop_continuous_monitoring(monitor_id: str) -> dict[str, Any]:
    """Stop continuous monitoring for a control"""
    success = _monitor.stop_monitoring(monitor_id)

    if success:
        return {
            "monitor_id": monitor_id,
            "status": "stopped",
            "message": "Continuous monitoring stopped successfully"
        }
    else:
        return {
            "monitor_id": monitor_id,
            "status": "error",
            "message": "Monitor not found or already stopped"
        }


@app.tool()
async def get_monitoring_status() -> dict[str, Any]:
    """Get status of all monitoring activities"""
    return _monitor.get_monitoring_status()


@app.tool()
async def run_manual_check(control_id: str, connector_id: Optional[str] = None) -> dict[str, Any]:
    """Run a manual compliance check for a control"""
    await _ensure_initialized()

    # Ensure AWS connector is available if requested
    if connector_id and connector_id.startswith("aws"):
        connector = connector_registry.get_connector(connector_id)
        if not connector:
            aws_config = {"connector_id": connector_id, "name": "AWS Connector"}
            connector = connector_registry.create_connector("aws", aws_config)
            if connector:
                await connector.connect()
                _monitor.register_connector(connector_id, connector)

    result = await _monitor.run_immediate_check(control_id, connector_id)

    # Record the check in history
    _storage.record_monitoring_check({
        "control_id": control_id,
        "check_type": "manual",
        "connector_id": connector_id,
        "status": result.get("status", "unknown"),
        "result_details": result,
        "evidence_paths": result.get("evidence_paths", [])
    })

    return result


@app.tool()
async def execute_compliance_workflow(
    target_controls: list[str],
    workflow_type: str = "compliance_assessment",
    baseline: str = "moderate"
) -> dict[str, Any]:
    """Execute an automated compliance workflow (Strand)"""
    await _ensure_initialized()

    # Register strand definitions
    _orchestrator.register_strand_definition(
        "compliance_assessment",
        "Compliance Assessment Workflow",
        "Automated compliance assessment with gap analysis and remediation planning",
        create_compliance_assessment_strand
    )

    # Create and execute strand
    strand = _orchestrator.create_strand(
        workflow_type,
        target_controls,
        baseline=baseline
    )

    result = await _orchestrator.execute_strand_async(strand)

    return result


@app.tool()
async def get_workflow_history(workflow_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get execution history for a workflow"""
    await _ensure_initialized()

    return _storage.get_workflow_runs(workflow_id, limit)


@app.tool()
async def get_active_workflows() -> list[dict[str, Any]]:
    """Get all currently active workflows"""
    return _orchestrator.get_active_strands()


@app.tool()
async def get_assessment_history(limit: int = 50) -> list[dict[str, Any]]:
    """Get historical assessment data"""
    await _ensure_initialized()

    return _storage.get_assessments(limit=limit)


@app.tool()
async def get_assessment_trends(days: int = 30) -> dict[str, Any]:
    """Get assessment trends over time"""
    await _ensure_initialized()

    return _storage.get_assessment_trends(days)


@app.tool()
async def save_assessment(assessment_data: dict[str, Any]) -> dict[str, Any]:
    """Save assessment results to history"""
    await _ensure_initialized()

    assessment_id = _storage.save_assessment(assessment_data)

    return {
        "assessment_id": assessment_id,
        "status": "saved",
        "timestamp": datetime.now().isoformat()
    }


@app.tool()
async def create_remediation_action(
    control_id: str,
    action_type: str,
    description: str,
    priority: str = "medium",
    assessment_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    due_date: Optional[str] = None
) -> dict[str, Any]:
    """Create a remediation action for a control"""
    await _ensure_initialized()

    # Validate priority
    if priority not in ["critical", "high", "medium", "low"]:
        raise ValueError("Priority must be one of: critical, high, medium, low")

    # Generate implementation steps based on control and action type
    implementation_steps = []
    evidence_required = []

    if action_type == "implement":
        implementation_steps = [
            f"Design implementation approach for {control_id}",
            f"Configure {control_id} controls in the environment",
            "Test implementation",
            "Document implementation",
            "Verify effectiveness"
        ]
        evidence_required = [
            f"Screenshots of {control_id} configuration",
            f"Test results for {control_id} implementation",
            "Documentation of implementation steps"
        ]
    elif action_type == "enhance":
        implementation_steps = [
            f"Assess current {control_id} implementation",
            "Identify enhancement opportunities",
            f"Implement {control_id} enhancements",
            "Test enhanced controls",
            "Update documentation"
        ]
        evidence_required = [
            f"Assessment report for current {control_id} implementation",
            f"Enhancement test results for {control_id}"
        ]
    elif action_type == "document":
        implementation_steps = [
            f"Review current {control_id} documentation",
            f"Update {control_id} procedures",
            "Validate documentation accuracy",
            "Train relevant personnel"
        ]
        evidence_required = [
            f"Updated {control_id} documentation",
            "Training records"
        ]

    action_id = _storage.create_remediation_action({
        "control_id": control_id,
        "assessment_id": assessment_id,
        "action_type": action_type,
        "description": description,
        "priority": priority,
        "status": "pending",
        "assigned_to": assigned_to,
        "due_date": due_date,
        "implementation_steps": implementation_steps,
        "evidence_required": evidence_required
    })

    return {
        "action_id": action_id,
        "control_id": control_id,
        "status": "created",
        "message": f"Remediation action created for {control_id}"
    }


@app.tool()
async def get_remediation_actions(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    control_id: Optional[str] = None,
    limit: int = 100
) -> list[dict[str, Any]]:
    """Get remediation actions with optional filtering"""
    await _ensure_initialized()

    return _storage.get_remediation_actions(
        status_filter=status_filter,
        priority_filter=priority_filter,
        control_id=control_id,
        limit=limit
    )


@app.tool()
async def get_overdue_remediations() -> list[dict[str, Any]]:
    """Get all overdue remediation actions"""
    await _ensure_initialized()

    return _storage.get_overdue_remediation_actions()


@app.tool()
async def update_remediation_status(
    action_id: str,
    status: str,
    outcome: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Update the status of a remediation action"""
    await _ensure_initialized()

    # Validate status
    valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
    if status not in valid_statuses:
        raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")

    success = _storage.update_remediation_status(action_id, status, outcome)

    if success:
        return {
            "action_id": action_id,
            "status": status,
            "updated": True,
            "outcome": outcome
        }
    else:
        return {
            "action_id": action_id,
            "status": "error",
            "updated": False,
            "message": "Action not found or update failed"
        }


@app.tool()
async def register_connector(
    connector_type: str,
    config: dict[str, Any]
) -> dict[str, Any]:
    """Register a new connector for external system integration"""
    connector = connector_registry.create_connector(connector_type, config)

    if connector:
        # Save connector in storage
        connector_id = _storage.register_connector({
            "name": config.get("name", connector.connector_id),
            "type": connector_type,
            "config": config,
            "status": "active"
        })

        # Register with monitor system
        _monitor.register_connector(connector.connector_id, connector)

        return {
            "connector_id": connector_id,
            "type": connector_type,
            "status": "registered",
            "message": f"Connector '{connector.name}' registered successfully"
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to register connector of type '{connector_type}'"
        }


@app.tool()
async def list_connectors() -> list[dict[str, Any]]:
    """List all registered connectors"""
    return connector_registry.list_connectors()


@app.tool()
async def get_monitoring_history(
    control_id: Optional[str] = None,
    days: int = 7
) -> list[dict[str, Any]]:
    """Get monitoring check history"""
    await _ensure_initialized()

    return _monitor.get_all_monitoring_history(days) if control_id is None else _monitor.get_control_monitoring_history(control_id, days)


@app.tool()
async def gap_analysis_with_history(
    implemented_controls: list[str],
    target_baseline: str = "moderate",
    create_remediations: bool = True
) -> dict[str, Any]:
    """Perform gap analysis and save results to history with optional remediation planning"""
    # Perform the analysis
    from .analysis_tools import NISTAnalysisTools
    analysis = NISTAnalysisTools(nist_server.loader)
    result = await analysis.gap_analysis(implemented_controls, target_baseline)

    # Save to history
    await _ensure_initialized()
    assessment_id = _storage.save_assessment({
        "assessment_type": "gap_analysis_with_history",
        "target_baseline": target_baseline,
        "input_controls": implemented_controls,
        "implemented_controls": implemented_controls,
        "results": result,
        "compliance_score": result.get("compliance_percentage"),
        "created_by": "gap_analysis_with_history_tool"
    })

    # Create remediation actions for missing controls if requested
    if create_remediations:
        missing_controls = result.get("missing_controls", {}).get("controls", [])
        remediation_actions = []

        for control_id in missing_controls:
            action_id = _storage.create_remediation_action({
                "control_id": control_id,
                "assessment_id": assessment_id,
                "action_type": "implement",
                "description": f"Implement missing control {control_id} to achieve {target_baseline} baseline compliance",
                "priority": "high",
                "status": "pending",
                "implementation_steps": [
                    f"Review {control_id} requirements and existing implementations",
                    f"Design {control_id} implementation approach",
                    f"Implement {control_id} in the target environment",
                    f"Test {control_id} implementation",
                    f"Document {control_id} implementation and evidence"
                ],
                "evidence_required": [
                    f"Screenshots of {control_id} configuration",
                    f"Test results demonstrating {control_id} effectiveness",
                    f"Documentation of {control_id} implementation"
                ]
            })
            remediation_actions.append({
                "control_id": control_id,
                "action_id": action_id,
                "action_type": "implement"
            })

        result["remediation_actions_created"] = len(remediation_actions)
        result["remediation_details"] = remediation_actions

    result["assessment_id"] = assessment_id
    result["saved_to_history"] = True

    return result


def main() -> None:
    """Entry point for the MCP server"""
    app.run()


if __name__ == "__main__":
    main()
