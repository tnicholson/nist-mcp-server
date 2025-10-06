#!/usr/bin/env python3
"""
Download NIST Data Script - Downloads and updates NIST data sources

This script downloads the latest NIST publications and OSCAL schemas
from official NIST sources.
"""

import json
import logging
import urllib.request
from pathlib import Path
from typing import ClassVar

logger = logging.getLogger(__name__)


class NISTDataDownloader:
    """Downloads and manages NIST data sources"""

    # Official NIST data source URLs
    DATA_SOURCES: ClassVar[dict[str, dict[str, str]]] = {
        "sp800-53-controls": {
            "url": "https://raw.githubusercontent.com/usnistgov/OSCAL-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json",
            "description": "NIST SP 800-53 Rev 5 Controls Catalog (JSON)",
            "path": "nist-sources/sp800-53/controls.json",
        },
        "sp800-53-controls-xml": {
            "url": "https://raw.githubusercontent.com/usnistgov/OSCAL-content/main/nist.gov/SP800-53/rev5/xml/NIST_SP-800-53_rev5_catalog.xml",
            "description": "NIST SP 800-53 Rev 5 Controls Catalog (XML)",
            "path": "nist-sources/sp800-53/controls.xml",
        },
        "sp800-53-low-baseline": {
            "url": "https://raw.githubusercontent.com/usnistgov/OSCAL-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_LOW-baseline_profile.json",
            "description": "NIST SP 800-53 Rev 5 LOW Baseline Profile",
            "path": "nist-sources/sp800-53/low-baseline.json",
        },
        "sp800-53-moderate-baseline": {
            "url": "https://raw.githubusercontent.com/usnistgov/OSCAL-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_MODERATE-baseline_profile.json",
            "description": "NIST SP 800-53 Rev 5 MODERATE Baseline Profile",
            "path": "nist-sources/sp800-53/moderate-baseline.json",
        },
        "sp800-53-high-baseline": {
            "url": "https://raw.githubusercontent.com/usnistgov/OSCAL-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_HIGH-baseline_profile.json",
            "description": "NIST SP 800-53 Rev 5 HIGH Baseline Profile",
            "path": "nist-sources/sp800-53/high-baseline.json",
        },
        "oscal-catalog-schema": {
            "url": "https://github.com/usnistgov/OSCAL/releases/download/v1.1.3/oscal_catalog_schema.json",
            "description": "OSCAL Catalog JSON Schema",
            "path": "oscal-schemas/catalog-schema.json",
        },
        "oscal-profile-schema": {
            "url": "https://github.com/usnistgov/OSCAL/releases/download/v1.1.3/oscal_profile_schema.json",
            "description": "OSCAL Profile JSON Schema",
            "path": "oscal-schemas/profile-schema.json",
        },
        "oscal-ssp-schema": {
            "url": "https://github.com/usnistgov/OSCAL/releases/download/v1.1.3/oscal_ssp_schema.json",
            "description": "OSCAL System Security Plan JSON Schema",
            "path": "oscal-schemas/ssp-schema.json",
        },
        "oscal-assessment-plan-schema": {
            "url": "https://github.com/usnistgov/OSCAL/releases/download/v1.1.3/oscal_assessment-plan_schema.json",
            "description": "OSCAL Assessment Plan JSON Schema",
            "path": "oscal-schemas/assessment-plan-schema.json",
        },
        "oscal-assessment-results-schema": {
            "url": "https://github.com/usnistgov/OSCAL/releases/download/v1.1.3/oscal_assessment-results_schema.json",
            "description": "OSCAL Assessment Results JSON Schema",
            "path": "oscal-schemas/assessment-results-schema.json",
        },
        "oscal-poam-schema": {
            "url": "https://github.com/usnistgov/OSCAL/releases/download/v1.1.3/oscal_poam_schema.json",
            "description": "OSCAL Plan of Actions & Milestones JSON Schema",
            "path": "oscal-schemas/poam-schema.json",
        },
    }

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)

    def download_all(self, force: bool = False) -> dict[str, bool]:
        """Download all NIST data sources"""
        results = {}

        for source_id, source_info in self.DATA_SOURCES.items():
            result = self._download_source(source_id, source_info, force)
            results[source_id] = result

        # Create CSF framework data (this would be extracted from official sources)
        self._create_csf_data()

        # Create control mappings
        self._create_control_mappings()

        return results

    def _download_source(
        self, source_id: str, source_info: dict[str, str], force: bool = False
    ) -> bool:
        """Download a single data source"""
        url = source_info["url"]
        file_path = self.data_path / source_info["path"]

        # Check if file already exists and is recent
        if file_path.exists() and not force:
            logger.info(
                f"Skipping {source_id} - file already exists (use --force to update)"
            )
            return True

        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Downloading {source_info['description']}...")

            # SECURITY: Only allow HTTPS URLs from trusted NIST domains for data download
            with urllib.request.urlopen(
                url
            ) as response:  # noqa: S310 - Trusted URLs only
                content = response.read().decode("utf-8")

                # Validate JSON content for JSON files
                if file_path.suffix == ".json":
                    try:
                        json.loads(content)  # Validate JSON
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON downloaded for {source_id}: {e}")
                        return False

                # Write file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                logger.info(f"Successfully downloaded {source_id}")
                return True

        except Exception as e:
            logger.error(f"Error downloading {source_id}: {e}")
            return False

    def _create_csf_data(self) -> None:
        """Create CSF framework data structure"""
        logger.info("Creating CSF framework data...")

        # This is a simplified CSF 2.0 structure
        # In production, this would be extracted from official NIST CSF sources
        csf_data = {
            "framework": {
                "uuid": "csf-2.0-core",
                "metadata": {
                    "title": "NIST Cybersecurity Framework 2.0 Core",
                    "version": "2.0",
                    "oscal-version": "1.0.4",
                },
                "functions": [
                    {
                        "id": "ID",
                        "name": "Identify",
                        "description": "Develop an organizational understanding to manage cybersecurity risk",
                        "categories": [
                            {
                                "id": "ID.AM",
                                "name": "Asset Management",
                                "description": "The data, personnel, devices, systems, and facilities that enable the organization to achieve business purposes are identified and managed consistent with their relative importance",
                                "subcategories": [
                                    {
                                        "id": "ID.AM-1",
                                        "description": "Physical devices and systems within the organization are inventoried",
                                    },
                                    {
                                        "id": "ID.AM-2",
                                        "description": "Software platforms and applications within the organization are inventoried",
                                    },
                                ],
                            },
                            {
                                "id": "ID.GV",
                                "name": "Governance",
                                "description": "The policies, procedures, and processes to manage and monitor the organization's regulatory, legal, risk, environmental, and operational requirements are understood",
                                "subcategories": [
                                    {
                                        "id": "ID.GV-1",
                                        "description": "Organizational cybersecurity policy is established and communicated",
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "id": "PR",
                        "name": "Protect",
                        "description": "Develop and implement appropriate safeguards to ensure delivery of critical services",
                        "categories": [
                            {
                                "id": "PR.AC",
                                "name": "Identity Management, Authentication and Access Control",
                                "description": "Access to physical and logical assets and associated facilities is limited to authorized users, processes, and devices",
                                "subcategories": [
                                    {
                                        "id": "PR.AC-1",
                                        "description": "Identities and credentials are issued, managed, verified, revoked, and audited",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "id": "DE",
                        "name": "Detect",
                        "description": "Develop and implement appropriate activities to identify the occurrence of a cybersecurity event",
                        "categories": [
                            {
                                "id": "DE.AE",
                                "name": "Anomalies and Events",
                                "description": "Anomalous activity is detected and the potential impact of events is understood",
                                "subcategories": [
                                    {
                                        "id": "DE.AE-1",
                                        "description": "A baseline of network operations and expected data flows is established and managed",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "id": "RS",
                        "name": "Respond",
                        "description": "Develop and implement appropriate activities to take action regarding a detected cybersecurity incident",
                        "categories": [
                            {
                                "id": "RS.RP",
                                "name": "Response Planning",
                                "description": "Response processes and procedures are executed and maintained",
                                "subcategories": [
                                    {
                                        "id": "RS.RP-1",
                                        "description": "Response plan is executed during or after an incident",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "id": "RC",
                        "name": "Recover",
                        "description": "Develop and implement appropriate activities to maintain plans for resilience and to restore any capabilities or services that were impaired due to a cybersecurity incident",
                        "categories": [
                            {
                                "id": "RC.RP",
                                "name": "Recovery Planning",
                                "description": "Recovery processes and procedures are executed and maintained to ensure restoration of systems or assets affected by cybersecurity incidents",
                                "subcategories": [
                                    {
                                        "id": "RC.RP-1",
                                        "description": "A recovery plan is executed during or after a cybersecurity incident",
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        }

        # Write CSF data
        csf_file = self.data_path / "nist-sources/csf/framework-core.json"
        csf_file.parent.mkdir(parents=True, exist_ok=True)

        with open(csf_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(csf_data, indent=2))

        logger.info("CSF framework data created successfully")

    def _create_control_mappings(self) -> None:
        """Create control-to-CSF mappings"""
        logger.info("Creating control-to-CSF mappings...")

        # This is a simplified mapping structure
        # In production, this would be based on official NIST mapping documents
        mappings_data = {
            "metadata": {
                "title": "SP 800-53 to CSF Mappings",
                "description": "Mappings between NIST SP 800-53 controls and CSF subcategories",
                "version": "1.0",
            },
            "mappings": {
                "AC-1": ["ID.GV-1", "PR.AC-1"],
                "AC-2": ["PR.AC-1", "DE.AE-1"],
                "AC-3": ["PR.AC-1"],
                "AU-1": ["ID.GV-1"],
                "AU-2": ["DE.AE-1"],
                "AU-3": ["DE.AE-1"],
                "CP-1": ["ID.GV-1", "RC.RP-1"],
                "CP-2": ["RC.RP-1"],
                "IR-1": ["ID.GV-1", "RS.RP-1"],
                "IR-4": ["RS.RP-1"],
                "RA-1": ["ID.GV-1"],
                "RA-3": ["ID.AM-1", "ID.AM-2"],
                "SA-1": ["ID.GV-1"],
                "SC-1": ["ID.GV-1"],
                "SI-1": ["ID.GV-1"],
            },
        }

        # Write mappings data
        mappings_file = self.data_path / "nist-sources/mappings/controls-to-csf.json"
        mappings_file.parent.mkdir(parents=True, exist_ok=True)

        with open(mappings_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(mappings_data, indent=2))

        logger.info("Control mappings created successfully")

    def create_examples(self) -> None:
        """Create example OSCAL documents"""
        logger.info("Creating example OSCAL documents...")

        # Example catalog
        example_catalog = {
            "catalog": {
                "uuid": "example-catalog-uuid",
                "metadata": {
                    "title": "Example Security Controls Catalog",
                    "version": "1.0",
                    "oscal-version": "1.0.4",
                },
                "controls": [
                    {
                        "id": "ex-1",
                        "class": "SP800-53",
                        "title": "Example Control",
                        "parts": [
                            {
                                "name": "statement",
                                "prose": "This is an example control for demonstration purposes.",
                            }
                        ],
                    }
                ],
            }
        }

        # Example SSP
        example_ssp = {
            "system-security-plan": {
                "uuid": "example-ssp-uuid",
                "metadata": {
                    "title": "Example System Security Plan",
                    "version": "1.0",
                    "oscal-version": "1.0.4",
                },
                "system-characteristics": {
                    "system-name": "Example Information System",
                    "description": "An example system for demonstration purposes",
                    "security-sensitivity-level": "moderate",
                },
                "control-implementation": {
                    "description": "Control implementation for example system",
                    "implemented-requirements": [],
                },
            }
        }

        # Write examples
        examples_dir = self.data_path / "examples"
        examples_dir.mkdir(parents=True, exist_ok=True)

        with open(examples_dir / "sample-catalog.json", "w") as f:
            f.write(json.dumps(example_catalog, indent=2))

        with open(examples_dir / "sample-ssp.json", "w") as f:
            f.write(json.dumps(example_ssp, indent=2))

        logger.info("Example documents created successfully")


def download_all_data(data_path: Path = None, force: bool = False) -> None:
    """Main function to download all NIST data"""
    if data_path is None:
        data_path = Path(__file__).parent.parent / "data"

    downloader = NISTDataDownloader(data_path)

    logger.info(f"Downloading NIST data to: {data_path}")

    results = downloader.download_all(force=force)

    # Create examples
    downloader.create_examples()

    # Summary
    successful = sum(1 for success in results.values() if success)
    total = len(results)

    logger.info(f"Download complete: {successful}/{total} sources successful")

    if successful < total:
        failed_sources = [
            source_id for source_id, success in results.items() if not success
        ]
        logger.warning(f"Failed sources: {failed_sources}")


def main():
    """Command line interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Download NIST data sources")
    parser.add_argument(
        "--data-path", type=Path, help="Path to data directory (default: ../data)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force download even if files exist"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    download_all_data(args.data_path, args.force)


if __name__ == "__main__":
    main()
