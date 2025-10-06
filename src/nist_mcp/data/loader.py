"""NIST Data Loader - Handles loading and caching of NIST data sources"""

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import aiofiles

logger = logging.getLogger(__name__)


class NISTDataLoader:
    """Handles loading and caching of NIST data sources"""

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self._controls_cache: dict[str, Any] | None = None
        self._csf_cache: dict[str, Any] | None = None
        self._mappings_cache: dict[str, Any] | None = None
        self._schemas_cache: dict[str, Any] | None = None
        self._baselines_cache: dict[str, Any] | None = None

    async def initialize(self) -> None:
        """Initialize the data loader and verify data sources exist"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data path does not exist: {self.data_path}")

        # Verify key data files exist
        required_files = [
            "nist-sources/sp800-53/controls.json",
            "nist-sources/csf/framework-core.json",
            "nist-sources/mappings/controls-to-csf.json",
        ]

        missing_files = []
        for file_path in required_files:
            full_path = self.data_path / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            logger.warning(f"Missing data files: {missing_files}")
            logger.info(
                "Run 'python scripts/download_nist_data.py' to download required data"
            )

    async def load_controls(self, force_reload: bool = False) -> dict[str, Any]:
        """Load NIST SP 800-53 controls from JSON file"""
        if self._controls_cache is not None and not force_reload:
            return self._controls_cache

        controls_file = self.data_path / "nist-sources/sp800-53/controls.json"

        if not controls_file.exists():
            # Try XML format as fallback
            xml_file = self.data_path / "nist-sources/sp800-53/controls.xml"
            if xml_file.exists():
                logger.info("JSON controls file not found, parsing XML...")
                self._controls_cache = await self._parse_controls_xml(xml_file)
            else:
                raise FileNotFoundError(f"Controls file not found: {controls_file}")
        else:
            async with aiofiles.open(controls_file, encoding="utf-8") as f:
                content = await f.read()
                self._controls_cache = json.loads(content)

        # Count controls across all groups
        total_controls = 0
        for group in self._controls_cache.get("catalog", {}).get("groups", []):
            total_controls += len(group.get("controls", []))
        logger.info(f"Loaded {total_controls} controls")
        return self._controls_cache

    async def load_csf(self, force_reload: bool = False) -> dict[str, Any]:
        """Load NIST Cybersecurity Framework data"""
        if self._csf_cache is not None and not force_reload:
            return self._csf_cache

        csf_file = self.data_path / "nist-sources/csf/framework-core.json"

        if not csf_file.exists():
            raise FileNotFoundError(f"CSF file not found: {csf_file}")

        async with aiofiles.open(csf_file, encoding="utf-8") as f:
            content = await f.read()
            self._csf_cache = json.loads(content)

        logger.info(
            f"Loaded CSF with {len(self._csf_cache.get('functions', []))} functions"
        )
        return self._csf_cache

    async def load_control_mappings(self, force_reload: bool = False) -> dict[str, Any]:
        """Load control-to-CSF mappings"""
        if self._mappings_cache is not None and not force_reload:
            return self._mappings_cache

        mappings_file = self.data_path / "nist-sources/mappings/controls-to-csf.json"

        if not mappings_file.exists():
            logger.warning(f"Mappings file not found: {mappings_file}")
            # Create empty mappings structure
            self._mappings_cache = {"mappings": {}}
            return self._mappings_cache

        async with aiofiles.open(mappings_file, encoding="utf-8") as f:
            content = await f.read()
            self._mappings_cache = json.loads(content)

        logger.info(
            f"Loaded {len(self._mappings_cache.get('mappings', {}))} control mappings"
        )
        return self._mappings_cache

    async def load_baseline_profiles(
        self, force_reload: bool = False
    ) -> dict[str, Any]:
        """Load NIST baseline profiles (Low, Moderate, High)"""
        if (
            hasattr(self, "_baselines_cache")
            and self._baselines_cache is not None
            and not force_reload
        ):
            return self._baselines_cache

        baselines = {}
        baseline_files = {
            "low": "nist-sources/sp800-53/low-baseline.json",
            "moderate": "nist-sources/sp800-53/moderate-baseline.json",
            "high": "nist-sources/sp800-53/high-baseline.json",
        }

        for baseline_name, filename in baseline_files.items():
            baseline_file = self.data_path / filename
            if baseline_file.exists():
                async with aiofiles.open(baseline_file, encoding="utf-8") as f:
                    content = await f.read()
                    baselines[baseline_name] = json.loads(content)
            else:
                logger.warning(f"Baseline file not found: {baseline_file}")

        self._baselines_cache = baselines
        logger.info(f"Loaded {len(baselines)} baseline profiles")
        return baselines

    async def load_oscal_schemas(self, force_reload: bool = False) -> dict[str, Any]:
        """Load OSCAL JSON schemas"""
        if self._schemas_cache is not None and not force_reload:
            return self._schemas_cache

        schemas_dir = self.data_path / "oscal-schemas"

        if not schemas_dir.exists():
            logger.warning(f"OSCAL schemas directory not found: {schemas_dir}")
            self._schemas_cache = {"schemas": {}}
            return self._schemas_cache

        schemas = {}
        schema_files = {
            "catalog": "catalog-schema.json",
            "profile": "profile-schema.json",
            "ssp": "ssp-schema.json",
            "assessment-plan": "assessment-plan-schema.json",
            "assessment-results": "assessment-results-schema.json",
            "poam": "poam-schema.json",
        }

        for schema_type, filename in schema_files.items():
            schema_file = schemas_dir / filename
            if schema_file.exists():
                async with aiofiles.open(schema_file, encoding="utf-8") as f:
                    content = await f.read()
                    schemas[schema_type] = json.loads(content)
            else:
                logger.warning(f"Schema file not found: {schema_file}")

        self._schemas_cache = {"schemas": schemas}
        logger.info(f"Loaded {len(schemas)} OSCAL schemas")
        return self._schemas_cache

    async def _parse_controls_xml(self, xml_file: Path) -> dict[str, dict[str, Any]]:
        """Parse controls from XML format (fallback when JSON not available)"""
        logger.info(f"Parsing XML controls file: {xml_file}")

        async with aiofiles.open(xml_file, encoding="utf-8") as f:
            xml_content = await f.read()

        root = ET.fromstring(xml_content)

        # Parse XML structure - this is a simplified parser
        # In production, you'd want more robust XML parsing based on actual NIST XML schema
        controls: list[dict[str, Any]] = []

        # Look for control elements (adjust XPath based on actual XML structure)
        for control_elem in root.findall(".//control"):
            control_id = control_elem.get("id", "")

            title_elem = control_elem.find(".//title")
            title = title_elem.text if title_elem is not None else ""

            # Extract other control properties
            control: dict[str, Any] = {
                "id": control_id,
                "title": title,
                "class": "SP800-53",
                "parts": [],
            }

            # Parse control parts (statement, guidance, etc.)
            for part_elem in control_elem.findall(".//part"):
                part_name = part_elem.get("name", "")
                part_prose = part_elem.find(".//prose")
                part_text = part_prose.text if part_prose is not None else ""

                if isinstance(control["parts"], list):
                    control["parts"].append({"name": part_name, "prose": part_text})

            controls.append(control)

        return {
            "catalog": {
                "uuid": "generated-from-xml",
                "metadata": {
                    "title": "NIST SP 800-53 Rev 5 Controls (parsed from XML)",
                    "version": "5.0",
                },
                "controls": controls,
            }
        }

    def get_control_by_id(
        self, controls_data: dict[str, Any], control_id: str
    ) -> dict[str, Any] | None:
        """Find a specific control by ID"""
        # Controls are nested in groups in OSCAL format
        groups = controls_data.get("catalog", {}).get("groups", [])

        for group in groups:
            controls = group.get("controls", [])
            for control in controls:
                if control.get("id", "").upper() == control_id.upper():
                    return control

        return None

    def search_controls_by_keyword(
        self,
        controls_data: dict[str, Any],
        keyword: str,
        family: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search controls by keyword in title or content"""
        # Controls are nested in groups in OSCAL format
        matches = []
        keyword_lower = keyword.lower()

        groups = controls_data.get("catalog", {}).get("groups", [])
        for group in groups:
            controls = group.get("controls", [])
            for control in controls:
                control_id = control.get("id", "")

                # Filter by family if specified
                if family and not control_id.startswith(family.upper()):
                    continue

                # Search in title
                title = control.get("title", "").lower()
                if keyword_lower in title:
                    matches.append(control)
                    continue

                # Search in control parts/content
                parts = control.get("parts", [])
                if isinstance(parts, list):
                    for part in parts:
                        prose = part.get("prose", "").lower()
                        if keyword_lower in prose:
                            matches.append(control)
                            break

                if len(matches) >= limit:
                    return matches[:limit]

        return matches[:limit]

    def get_controls_by_family(
        self, controls_data: dict[str, Any], family: str
    ) -> list[dict[str, Any]]:
        """Get all controls in a specific family"""
        # Controls are nested in groups in OSCAL format
        family_controls = []
        family_upper = family.upper()

        groups = controls_data.get("catalog", {}).get("groups", [])
        for group in groups:
            controls = group.get("controls", [])
            for control in controls:
                control_id = control.get("id", "")
                if control_id.startswith(family_upper):
                    family_controls.append(control)

        return family_controls
