"""Control Tools - NIST SP 800-53 control management tools"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ControlTools:
    """Tools for managing NIST SP 800-53 controls"""

    def __init__(self, data_loader: Any) -> None:
        self.data_loader = data_loader

    async def get_control(self, control_id: str) -> dict[str, Any]:
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
        self, query: str, family: str | None = None, limit: int = 10
    ) -> dict[str, Any]:
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

    async def get_control_family(self, family: str) -> dict[str, Any]:
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

    async def get_control_mappings(self, control_id: str) -> dict[str, Any]:
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

    async def get_control_baselines(self, baseline: str = "moderate") -> dict[str, Any]:
        """Get controls for a specific baseline (low, moderate, high)"""
        baseline = baseline.lower()

        if baseline not in ["low", "moderate", "high"]:
            raise ValueError("Baseline must be 'low', 'moderate', or 'high'")

        # Load the actual baseline profiles from JSON files
        baseline_profiles = await self.data_loader.load_baseline_profiles()

        if baseline not in baseline_profiles:
            raise ValueError(f"Baseline profile '{baseline}' not found")

        # Extract control IDs from OSCAL profile format
        baseline_control_ids = self._extract_baseline_control_ids(
            baseline_profiles[baseline]
        )

        controls_data = await self.data_loader.load_controls()

        # Extract all controls from all groups (OSCAL catalog structure)
        controls_db = []
        groups = controls_data.get("catalog", {}).get("groups", [])
        for group in groups:
            controls_db.extend(group.get("controls", []))

        selected_controls = []
        found_control_ids = set()

        for control in controls_db:
            control_id = control.get("id", "").upper()
            # Check if control is in baseline (normalized to uppercase)
            if control_id in baseline_control_ids:
                selected_controls.append(
                    {
                        "id": control_id,
                        "title": control.get("title", ""),
                        "family": control_id[:2],
                    }
                )
                found_control_ids.add(control_id)

        # Check for any baseline controls that weren't found in the controls database
        missing_controls = baseline_control_ids - found_control_ids

        result = {
            "baseline": baseline.title(),
            "total_controls": len(selected_controls),
            "controls": selected_controls,
        }

        if missing_controls:
            result["missing_controls"] = sorted(list(missing_controls))
            result["missing_count"] = len(missing_controls)

        return result

    def _get_family_info(self, family: str) -> dict[str, str]:
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

    def _extract_baseline_control_ids(
        self, baseline_profile: dict[str, Any]
    ) -> set[str]:
        """Extract control IDs from OSCAL baseline profile format"""
        control_ids: set[str] = set()

        # Navigate OSCAL profile structure: profile.imports[0].include-controls[0].with-ids
        imports = baseline_profile.get("profile", {}).get("imports", [])
        if not imports:
            return control_ids

        include_controls = imports[0].get("include-controls", [])
        if not include_controls:
            return control_ids

        with_ids = include_controls[0].get("with-ids", [])

        # Convert to uppercase and normalize format (ac-1 -> AC-1, ac-2.1 -> AC-2.1)
        for control_id in with_ids:
            if isinstance(control_id, str):
                # Convert lowercase with dashes to uppercase with dashes
                normalized_id = control_id.upper()
                # Handle special cases like ac-2.1 -> AC-2.1
                if "." in normalized_id:
                    parts = normalized_id.split(".", 1)
                    normalized_id = f"{parts[0].upper()}.{parts[1]}"
                control_ids.add(normalized_id)

        return control_ids
