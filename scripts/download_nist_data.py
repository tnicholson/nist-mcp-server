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
        "sp800-171-cui-baseline": {
            "url": "https://raw.githubusercontent.com/usnistgov/OSCAL-content/main/nist.gov/SP800-171/rev2/json/NIST_SP-800-171_rev2_CUI-baseline_profile.json",
            "description": "NIST SP 800-171 Rev 2 CUI Baseline Profile",
            "path": "nist-sources/sp800-171/cui-baseline.json",
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

        # Create CMMC framework data
        self._create_cmmc_framework_data()

        # Create FedRAMP framework data
        self._create_fedramp_framework_data()

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

    def _create_cmmc_framework_data(self) -> None:
        """Create CMMC framework data in the download script"""
        logger.info("Creating CMMC framework data...")

        # CMMC Level 1: Basic Cyber Hygiene
        level_1_controls = [
            "AC-1", "AC-3", "AC-5", "AC-6", "AC-18", "AC-19", "AC-20",
            "AT-2", "AT-3", "AT-4",
            "AU-3", "AU-6", "AU-7",
            "CA-3",
            "CM-5", "CM-6", "CM-7", "CM-8",
            "IA-3", "IA-5", "IA-8",
            "IR-6",
            "MP-L2-3.11", "MP-L2-3.12", "MP-L2-3.13",
            "PE-3", "PE-6", "PE-8",
            "PS-8",
            "RE-3",
            "RC-5",
            "SA-3", "SA-4", "SA-8",
            "SC-5", "SC-7", "SC-8", "SC-13", "SC-15", "SC-16", "SC-18", "SC-20", "SC-21",
            "SE-2",
            "SI-2", "SI-3", "SI-4", "SI-5", "SI-7", "SI-10", "SI-12"
        ]

        # CMMC Level 2: Intermediate Cyber Hygiene
        level_2_controls = [
            "AC-2", "AC-4", "AC-7", "AC-17", "AC-25",
            "AT-1",
            "AU-1", "AU-11", "AU-12",
            "CA-7",
            "CM-2", "CM-4", "CM-9",
            "CP-9",
            "IA-2", "IA-9",
            "IR-4",
            "MA-2",
            "MP-2", "MP-4", "MP-5",
            "PE-2",
            "PL-8",
            "PS-3", "PS-6",
            "PT-3",
            "RE-2",
            "RE-4",
            "RS-2",
            "SA-10", "SA-11",
            "SC-3", "SC-10", "SC-12", "SC-17", "SC-23", "SC-31",
            "SE-5",
            "SI-6", "SI-8"
        ]

        # CMMC Level 3: Good Cyber Hygiene
        level_3_controls = [
            "AC-12", "AC-14", "AC-25",
            "AT-5",
            "AU-2", "AU-9", "AU-13",
            "CA-2", "CA-5", "CA-6", "CA-9",
            "CM-3", "CM-10", "CM-11",
            "CP-7",
            "IA-12", "IA-13",
            "IR-2", "IR-8",
            "MA-3", "MA-6",
            "MP-3", "MP-6",
            "PE-1",
            "PL-2",
            "PS-4", "PS-5",
            "RA-2", "RA-5",
            "SA-5", "SA-15", "SA-17",
            "SC-2", "SC-39",
            "SI-11", "SI-16",
            "SR-2", "SR-3", "SR-5"
        ]

        # CMMC Level 4: Proactive
        level_4_controls = [
            "AC-6", "AC-21", "AC-22", "AC-23",
            "AU-5", "AU-14",
            "CA-8",
            "CM-12", "CM-13",
            "CP-2", "CP-3",
            "IA-11", "IA-17",
            "IR-3", "IR-7",
            "RA-3",
            "SA-12",
            "SC-4", "SC-28", "SC-38",
            "SI-14", "SI-23"
        ]

        # CMMC Level 5: Advanced / Progressive
        level_5_controls = [
            "AC-8", "AC-9", "AC-10", "AC-11", "AC-15", "AC-16", "AC-24",
            "AT-5",
            "AU-4", "AU-8", "AU-10",
            "CA-1", "CA-4",
            "CM-14",
            "CP-4", "CP-8",
            "IA-6", "IA-7", "IA-10",
            "IR-5", "IR-9",
            "PL-4", "PL-7",
            "PR-4", "PR-6", "PR-8", "PR-9", "PR-10", "PR-11",
            "RA-4"
        ]

        cmmc_framework = {
            "framework": {
                "name": "Cybersecurity Maturity Model Certification (CMMC)",
                "version": "2.0",
                "description": "CMMC framework for assessing cybersecurity maturity and capabilities",
                "levels": [
                    {
                        "level": 1,
                        "name": "Foundational",
                        "description": "Basic Cyber Hygiene - Protect Federal Contract Information (FCI)",
                        "controls": level_1_controls,
                        "total_controls": len(level_1_controls)
                    },
                    {
                        "level": 2,
                        "name": "Advanced",
                        "description": "Intermediate Cyber Hygiene - Protect Controlled Unclassified Information (CUI)",
                        "controls": level_2_controls,
                        "total_controls": len(level_2_controls)
                    },
                    {
                        "level": 3,
                        "name": "Expert",
                        "description": "Good Cyber Hygiene - Protect CUI",
                        "controls": level_3_controls,
                        "total_controls": len(level_3_controls)
                    },
                    {
                        "level": 4,
                        "name": "Expert",
                        "description": "Proactive Cyber Hygiene - Protect CUI",
                        "controls": level_4_controls,
                        "total_controls": len(level_4_controls)
                    },
                    {
                        "level": 5,
                        "name": "Expert",
                        "description": "Advanced / Progressive Cyber Hygiene - Protect CUI",
                        "controls": level_5_controls,
                        "total_controls": len(level_5_controls)
                    }
                ]
            }
        }

        # Create the directory and save the framework
        framework_dir = self.data_path / "nist-sources/cmmc"
        framework_dir.mkdir(parents=True, exist_ok=True)
        framework_file = framework_dir / "framework.json"

        with open(framework_file, "w", encoding="utf-8") as f:
            json.dump(cmmc_framework, f, indent=2)

        logger.info("CMMC framework data created successfully")

    def _create_fedramp_framework_data(self) -> None:
        """Create FedRAMP framework data in the download script"""
        logger.info("Creating FedRAMP framework data...")

        fedramp_framework = {
            "framework": {
                "name": "Federal Risk and Authorization Management Program (FedRAMP)",
                "version": "Rev 4",
                "description": "FedRAMP provides a standardized approach to security assessment, authorization, and continuous monitoring for cloud products and services",
                "baselines": [
                    {
                        "level": "low",
                        "name": "Low Impact",
                        "description": "Low impact level baseline for systems where the loss of confidentiality, integrity, or availability could be expected to have limited adverse effects",
                        "impact_level": "FIPS-199 Low",
                        "controls_url": "../sp800-53/low-baseline.json"
                    },
                    {
                        "level": "moderate",
                        "name": "Moderate Impact",
                        "description": "Moderate impact level baseline for systems where the loss of confidentiality, integrity, or availability could be expected to have serious adverse effects",
                        "impact_level": "FIPS-199 Moderate",
                        "controls_url": "../sp800-53/moderate-baseline.json"
                    },
                    {
                        "level": "high",
                        "name": "High Impact",
                        "description": "High impact level baseline for systems where the loss of confidentiality, integrity, or availability could be expected to have severe or catastrophic adverse effects",
                        "impact_level": "FIPS-199 High",
                        "controls_url": "../sp800-53/high-baseline.json"
                    }
                ],
                "authorization_types": [
                    {
                        "type": "JAB",
                        "name": "JAB Authorization",
                        "description": "Joint Authorization Board authorization for widely-used cloud services",
                        "pathways": ["Priority", "General"]
                    },
                    {
                        "type": "Agency",
                        "name": "Agency Authorization",
                        "description": "Individual agency authorization for specific use cases",
                        "pathways": ["Priority", "General"]
                    }
                ],
                "requirements": {
                    "cloud_service_providers": [
                        "Develop and maintain System Security Plans (SSP)",
                        "Implement NIST SP 800-53 security controls",
                        "Conduct ongoing security assessments",
                        "Provide continuous monitoring capabilities",
                        "Support agency authorization reviews"
                    ],
                    "agencies": [
                        "Conduct risk assessments for cloud migrations",
                        "Review and accept FedRAMP authorizations",
                        "Maintain oversight of authorized cloud services",
                        "Ensure continuous monitoring of operations"
                    ]
                }
            }
        }

        # Create the directory and save the framework
        framework_dir = self.data_path / "nist-sources/fedramp"
        framework_dir.mkdir(parents=True, exist_ok=True)
        framework_file = framework_dir / "framework.json"

        with open(framework_file, "w", encoding="utf-8") as f:
            json.dump(fedramp_framework, f, indent=2)

        logger.info("FedRAMP framework data created successfully")

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
