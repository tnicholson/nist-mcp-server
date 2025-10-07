"""Framework-specific MCP tool endpoints"""

import logging
from typing import Any

from mcp.server import FastMCP

logger = logging.getLogger(__name__)


def register_framework_endpoints(app: FastMCP, loader: Any) -> None:
    """Register all framework-specific endpoints with the MCP app"""

    @app.tool()
    async def get_sp800171_baseline() -> dict[str, Any]:
        """Get NIST SP 800-171 CUI baseline controls"""
        try:
            baseline_data = await loader.load_sp800171_baseline()

            # Extract control IDs from OSCAL profile format
            control_ids = []
            imports = baseline_data.get("profile", {}).get("imports", [])
            if imports:
                include_controls = imports[0].get("include-controls", [])
                if include_controls:
                    with_ids = include_controls[0].get("with-ids", [])
                    control_ids = [
                        control_id for control_id in with_ids if isinstance(control_id, str)
                    ]

            controls_data = await loader.load_controls()

            # Get control details for baseline controls
            baseline_controls = []
            found_control_ids = set()

            for group in controls_data.get("catalog", {}).get("groups", []):
                for control in group.get("controls", []):
                    control_id = control.get("id", "").upper()
                    if control_id in [cid.upper() for cid in control_ids]:
                        baseline_controls.append(
                            {
                                "id": control_id,
                                "title": control.get("title", ""),
                                "family": control_id[:2],
                                "class": "SP800-171",
                            }
                        )
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
            catalog_data = await loader.load_sp800171_catalog()

            groups = catalog_data.get("catalog", {}).get("groups", [])
            total_controls = sum(len(group.get("controls", [])) for group in groups)

            return {
                "catalog": "NIST SP 800-171 Rev 2",
                "version": "2.0",
                "total_controls": total_controls,
                "families": len(groups),
                "groups": [
                    {
                        "id": group["id"],
                        "title": group["title"],
                        "controls_count": len(group.get("controls", [])),
                    }
                    for group in groups
                ],
                "description": "Complete catalog of 110 security requirements for protecting Controlled Unclassified Information (CUI)",
            }
        except Exception as e:
            logger.error(f"Error loading SP 800-171 catalog: {e}")
            raise

    @app.tool()
    async def get_sp800171_control(control_id: str) -> dict[str, Any]:
        """Get details for a specific SP 800-171 control"""
        try:
            catalog_data = await loader.load_sp800171_catalog()
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
                            "class": "SP800-171",
                        }

            raise ValueError(f"SP 800-171 control {control_id} not found")
        except Exception as e:
            logger.error(f"Error getting SP 800-171 control {control_id}: {e}")
            raise

    @app.tool()
    async def get_sp800171_family(family: str) -> dict[str, Any]:
        """Get all SP 800-171 controls in a specific family"""
        try:
            catalog_data = await loader.load_sp800171_catalog()
            family = family.upper()

            for group in catalog_data.get("catalog", {}).get("groups", []):
                if group["id"] == family:
                    controls = []
                    for control in group.get("controls", []):
                        controls.append(
                            {
                                "id": control["id"],
                                "title": control["title"],
                                "sp800_53_mappings": control.get("sp800-53-mappings", []),
                            }
                        )

                    return {
                        "family": family,
                        "family_name": group["title"],
                        "total_controls": len(controls),
                        "controls": controls,
                        "description": group["description"],
                    }

            raise ValueError(f"SP 800-171 family {family} not found")
        except Exception as e:
            logger.error(f"Error getting SP 800-171 family {family}: {e}")
            raise

    @app.tool()
    async def sp800171_to_sp80053_mapping(control_ids: list[str]) -> dict[str, Any]:
        """Map SP 800-171 requirements to their corresponding SP 800-53 controls"""
        try:
            catalog_data = await loader.load_sp800171_catalog()
            sp80053_mappings = {}

            for control_id in control_ids:
                control_id = control_id.upper()
                sp80053_mappings[control_id] = []

                # Find the control in the catalog
                for group in catalog_data.get("catalog", {}).get("groups", []):
                    for control in group.get("controls", []):
                        if control.get("id", "").upper() == control_id:
                            sp80053_mappings[control_id] = control.get(
                                "sp800-53-mappings", []
                            )
                            break
                    if sp80053_mappings[control_id]:
                        break

            return {
                "sp800171_to_sp80053_mappings": sp80053_mappings,
                "total_sp800171_controls": len(control_ids),
                "controls_mapped": len([k for k, v in sp80053_mappings.items() if v]),
            }
        except Exception as e:
            logger.error(f"Error mapping SP 800-171 to SP 800-53: {e}")
            raise

    @app.tool()
    async def get_cmmc_framework() -> dict[str, Any]:
        """Get the complete CMMC framework structure"""
        try:
            cmmc_data = await loader.load_cmmc_framework()
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
            cmmc_data = await loader.load_cmmc_framework()

            level_data = None
            for lvl in cmmc_data.get("framework", {}).get("levels", []):
                if lvl.get("level") == level:
                    level_data = lvl
                    break

            if not level_data:
                raise ValueError(f"CMMC Level {level} not found")

            controls_data = await loader.load_controls()

            # Get control details for level controls
            level_controls = []
            found_control_ids = set()

            # Search through all controls in catalog
            for group in controls_data.get("catalog", {}).get("groups", []):
                for control in group.get("controls", []):
                    control_id = control.get("id", "").upper()
                    if control_id in [
                        cid.upper() for cid in level_data.get("controls", [])
                    ]:
                        level_controls.append(
                            {
                                "id": control_id,
                                "title": control.get("title", ""),
                                "family": control_id[:2],
                                "class": "CMMC",
                            }
                        )
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
            cmmc_data = await loader.load_cmmc_framework()

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
                implemented_for_level = [
                    cid for cid in implemented_controls_upper if cid in level_controls
                ]
                missing_for_level = [
                    cid for cid in level_controls if cid not in implemented_controls_upper
                ]

                level_compliance[level_name] = {
                    "required": len(level_controls),
                    "implemented": len(implemented_for_level),
                    "missing": len(missing_for_level),
                    "compliance_percentage": round(
                        (len(implemented_for_level) / len(level_controls)) * 100, 2
                    ),
                    "missing_controls": missing_for_level,
                }

            # Overall assessment
            total_required = len(required_controls)
            total_implemented = len(
                [cid for cid in implemented_controls_upper if cid in required_controls]
            )

            # Check if all controls for target level are implemented
            target_level_controls = required_by_level.get(f"Level {target_level}", [])
            has_target_level = all(
                cid in implemented_controls_upper for cid in target_level_controls
            )

            assessment_level = target_level if has_target_level else target_level - 1

            return {
                "assessment": {
                    "implemented_controls_count": len(implemented_controls),
                    "target_level": target_level,
                    "assessment_level": assessment_level,
                    "overall_compliance_percentage": round(
                        (total_implemented / total_required) * 100, 2
                    ),
                    "fully_compliant_to_target": has_target_level,
                    "total_required": total_required,
                    "total_implemented": total_implemented,
                    "total_missing": total_required - total_implemented,
                },
                "level_details": level_compliance,
                "recommendations": [
                    f"Achieve Level {target_level}"
                    if has_target_level
                    else f"Work towards Level {target_level}",
                    f"Implement missing {total_required - total_implemented} controls across all levels",
                ],
            }
        except Exception as e:
            logger.error(f"Error performing CMMC compliance assessment: {e}")
            raise

    @app.tool()
    async def get_fedramp_framework() -> dict[str, Any]:
        """Get the complete FedRAMP framework structure"""
        try:
            fedramp_data = await loader.load_fedramp_framework()
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
            fedramp_data = await loader.load_fedramp_framework()

            # Find the matching baseline
            target_baseline = None
            for baseline in fedramp_data.get("framework", {}).get("baselines", []):
                if baseline.get("level", "").lower() == impact_level:
                    target_baseline = baseline
                    break

            if not target_baseline:
                raise ValueError(
                    f"FedRAMP baseline not found for impact level: {impact_level}"
                )

            # Load the corresponding SP 800-53 baseline profile
            if impact_level == "low":
                baseline_data = await loader.load_baseline_profiles()
                baseline_profile = baseline_data.get("low", {})
            elif impact_level == "moderate":
                baseline_data = await loader.load_baseline_profiles()
                baseline_profile = baseline_data.get("moderate", {})
            else:  # high
                baseline_data = await loader.load_baseline_profiles()
                baseline_profile = baseline_data.get("high", {})

            # Extract control IDs from OSCAL profile format
            control_ids = []
            if baseline_profile:
                imports = baseline_profile.get("profile", {}).get("imports", [])
                if imports:
                    include_controls = imports[0].get("include-controls", [])
                    if include_controls:
                        with_ids = include_controls[0].get("with-ids", [])
                        control_ids = [
                            control_id
                            for control_id in with_ids
                            if isinstance(control_id, str)
                        ]

            controls_data = await loader.load_controls()

            # Get control details for baseline controls
            baseline_controls = []
            found_control_ids = set()

            for group in controls_data.get("catalog", {}).get("groups", []):
                for control in group.get("controls", []):
                    control_id = control.get("id", "").upper()
                    if control_id in [cid.upper() for cid in control_ids]:
                        baseline_controls.append(
                            {
                                "id": control_id,
                                "title": control.get("title", ""),
                                "family": control_id[:2],
                                "class": "FedRAMP",
                            }
                        )
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
            fedramp_data = await loader.load_fedramp_framework()

            # For simplicity, we'll use the moderate baseline as the primary assessment
            # In practice, this would be more sophisticated based on the service model
            baseline_data = await loader.load_baseline_profiles()
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
            implemented_count = len(
                [cid for cid in implemented_controls_upper if cid in required_control_ids]
            )
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
                    "available_pathways": pathways,
                },
                "fedramp_requirements": fedramp_data.get("framework", {}).get(
                    "requirements", {}
                ),
                "recommendations": [
                    f"Achieve at least 75% compliance before pursuing authorization (currently {compliance_percentage}%)",
                    f"Focus on implementing missing {missing_count} controls",
                    f"For {service_model.upper()} services, consider the guidance in FedRAMP Rev 4",
                    "Develop comprehensive System Security Plan (SSP)",
                    "Prepare for continuous monitoring requirements",
                ],
            }
        except Exception as e:
            logger.error(f"Error performing FedRAMP readiness assessment: {e}")
            raise
