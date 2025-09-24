"""
Control Tools - NIST SP 800-53 control management tools
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ControlTools:
    """Tools for managing NIST SP 800-53 controls"""

    def __init__(self, data_loader):
        self.data_loader = data_loader

    async def get_control(self, control_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific control"""
        controls_data = await self.data_loader.load_controls()

        control = self.data_loader.get_control_by_id(controls_data, control_id)

        if not control:
            raise ValueError(f"Control not found: {control_id}")

        # Enhance control data with additional information
        enhanced_control = {
            "id": control.get("id"),
            "title": control.get("title"),
            "class": control.get("class", "SP800-53"),
            "family": control.get("id", "")[:2],  # First two characters
            "parts": control.get("parts", []),
            "properties": control.get("props", []),
            "links": control.get("links", []),
        }

        # Add control enhancements if they exist
        controls = control.get("controls", [])
        if controls:
            enhanced_control["enhancements"] = controls

        return enhanced_control

    async def search_controls(
        self, query: str, family: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search controls by keyword or topic"""
        controls_data = await self.data_loader.load_controls()

        matches = self.data_loader.search_controls_by_keyword(
            controls_data, query, family, limit
        )

        # Return simplified control information for search results
        results = []
        for control in matches:
            result = {
                "id": control.get("id"),
                "title": control.get("title"),
                "family": control.get("id", "")[:2],
                "class": control.get("class", "SP800-53"),
            }

            # Add a snippet from the control content
            parts = control.get("parts", [])
            if parts:
                statement_part = next(
                    (part for part in parts if part.get("name") == "statement"),
                    parts[0],
                )
                prose = statement_part.get("prose", "")
                if prose:
                    # Truncate to reasonable length for search results
                    result["snippet"] = (
                        prose[:200] + "..." if len(prose) > 200 else prose
                    )

            results.append(result)

        return {
            "query": query,
            "family_filter": family,
            "total_results": len(results),
            "controls": results,
        }

    async def get_control_family(self, family: str) -> Dict[str, Any]:
        """Get all controls in a specific family"""
        if len(family) != 2:
            raise ValueError("Family must be 2 characters (e.g., 'AC', 'AU', 'CA')")

        controls_data = await self.data_loader.load_controls()

        family_controls = self.data_loader.get_controls_by_family(controls_data, family)

        if not family_controls:
            raise ValueError(f"No controls found for family: {family}")

        # Group by base control and enhancements
        base_controls = []
        enhancements = []

        for control in family_controls:
            control_id = control.get("id", "")

            # Check if this is an enhancement (contains parentheses)
            if "(" in control_id:
                enhancements.append(
                    {
                        "id": control_id,
                        "title": control.get("title", ""),
                        "base_control": control_id.split("(")[0],
                    }
                )
            else:
                base_controls.append(
                    {
                        "id": control_id,
                        "title": control.get("title", ""),
                        "class": control.get("class", "SP800-53"),
                    }
                )

        # Get family information
        family_info = self._get_family_info(family)

        return {
            "family": family.upper(),
            "name": family_info.get("name", f"{family.upper()} Family"),
            "description": family_info.get("description", ""),
            "base_controls": base_controls,
            "enhancements": enhancements,
            "total_controls": len(base_controls),
            "total_enhancements": len(enhancements),
        }

    async def get_control_mappings(self, control_id: str) -> Dict[str, Any]:
        """Get CSF mappings for a specific control"""
        mappings_data = await self.data_loader.load_control_mappings()

        # Look up mappings for this control
        mappings = mappings_data.get("mappings", {}).get(control_id.upper(), [])

        if not mappings:
            return {
                "control_id": control_id,
                "csf_mappings": [],
                "message": f"No CSF mappings found for control {control_id}",
            }

        return {
            "control_id": control_id,
            "csf_mappings": mappings,
            "total_mappings": len(mappings),
        }

    async def get_control_baselines(self, baseline: str = "moderate") -> Dict[str, Any]:
        """Get controls for a specific baseline (low, moderate, high)"""
        baseline = baseline.lower()

        if baseline not in ["low", "moderate", "high"]:
            raise ValueError("Baseline must be 'low', 'moderate', or 'high'")

        controls_data = await self.data_loader.load_controls()

        # This would typically be loaded from NIST baseline data
        # For now, we'll create a simplified baseline mapping
        baseline_controls = self._get_baseline_controls(baseline)

        selected_controls = []
        controls = controls_data.get("catalog", {}).get("controls", [])

        for control in controls:
            control_id = control.get("id", "")
            if control_id in baseline_controls:
                selected_controls.append(
                    {
                        "id": control_id,
                        "title": control.get("title", ""),
                        "family": control_id[:2],
                    }
                )

        return {
            "baseline": baseline.title(),
            "total_controls": len(selected_controls),
            "controls": selected_controls,
        }

    def _get_family_info(self, family: str) -> Dict[str, str]:
        """Get information about a control family"""
        families = {
            "AC": {
                "name": "Access Control",
                "description": "Controls for limiting system access",
            },
            "AU": {
                "name": "Audit and Accountability",
                "description": "Controls for system auditing",
            },
            "AT": {
                "name": "Awareness and Training",
                "description": "Security awareness and training",
            },
            "CM": {
                "name": "Configuration Management",
                "description": "System configuration controls",
            },
            "CP": {
                "name": "Contingency Planning",
                "description": "Emergency response planning",
            },
            "IA": {
                "name": "Identification and Authentication",
                "description": "User identity management",
            },
            "IR": {
                "name": "Incident Response",
                "description": "Security incident handling",
            },
            "MA": {"name": "Maintenance", "description": "System maintenance controls"},
            "MP": {
                "name": "Media Protection",
                "description": "Storage media protection",
            },
            "PE": {
                "name": "Physical and Environmental Protection",
                "description": "Physical security",
            },
            "PL": {"name": "Planning", "description": "Security planning controls"},
            "PS": {
                "name": "Personnel Security",
                "description": "Personnel security controls",
            },
            "RA": {
                "name": "Risk Assessment",
                "description": "Risk management controls",
            },
            "CA": {
                "name": "Assessment, Authorization, and Monitoring",
                "description": "Security assessment",
            },
            "SC": {
                "name": "System and Communications Protection",
                "description": "System security",
            },
            "SI": {
                "name": "System and Information Integrity",
                "description": "Information integrity",
            },
            "SA": {
                "name": "System and Services Acquisition",
                "description": "Acquisition security",
            },
            "PM": {
                "name": "Program Management",
                "description": "Security program management",
            },
        }

        return families.get(
            family.upper(), {"name": f"{family.upper()} Family", "description": ""}
        )

    def _get_baseline_controls(self, baseline: str) -> List[str]:
        """Get list of controls for a baseline (simplified mapping)"""
        # This is a simplified baseline mapping
        # In production, load this from official NIST baseline data

        baselines = {
            "low": [
                "AC-1",
                "AC-2",
                "AC-3",
                "AC-7",
                "AC-8",
                "AC-14",
                "AC-17",
                "AC-18",
                "AC-19",
                "AC-20",
                "AC-22",
                "AU-1",
                "AU-2",
                "AU-3",
                "AU-4",
                "AU-5",
                "AU-6",
                "AU-8",
                "AU-9",
                "AU-11",
                "AU-12",
                "AT-1",
                "AT-2",
                "AT-3",
                "AT-4",
                "CM-1",
                "CM-2",
                "CM-4",
                "CM-5",
                "CM-6",
                "CM-7",
                "CM-8",
                "CM-10",
                "CM-11",
                "CP-1",
                "CP-2",
                "CP-3",
                "CP-4",
                "CP-9",
                "CP-10",
            ],
            "moderate": [
                # Includes all low baseline controls plus additional ones
                "AC-1",
                "AC-2",
                "AC-3",
                "AC-4",
                "AC-5",
                "AC-6",
                "AC-7",
                "AC-8",
                "AC-11",
                "AC-12",
                "AC-14",
                "AC-17",
                "AC-18",
                "AC-19",
                "AC-20",
                "AC-21",
                "AC-22",
                "AU-1",
                "AU-2",
                "AU-3",
                "AU-4",
                "AU-5",
                "AU-6",
                "AU-7",
                "AU-8",
                "AU-9",
                "AU-10",
                "AU-11",
                "AU-12",
                "AT-1",
                "AT-2",
                "AT-3",
                "AT-4",
                "AT-5",
                "CM-1",
                "CM-2",
                "CM-3",
                "CM-4",
                "CM-5",
                "CM-6",
                "CM-7",
                "CM-8",
                "CM-9",
                "CM-10",
                "CM-11",
                "CP-1",
                "CP-2",
                "CP-3",
                "CP-4",
                "CP-6",
                "CP-7",
                "CP-8",
                "CP-9",
                "CP-10",
            ],
            "high": [
                # Includes all moderate baseline controls plus high-impact specific ones
                # This would be a much longer list in practice
            ],
        }

        controls = baselines.get(baseline, [])

        # For moderate and high, inherit from lower baselines
        if baseline == "moderate":
            controls.extend(baselines["low"])
        elif baseline == "high":
            controls.extend(baselines["moderate"])
            controls.extend(baselines["low"])

        return list(set(controls))  # Remove duplicates
