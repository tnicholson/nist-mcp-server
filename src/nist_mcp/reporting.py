"""Auditor-Ready Reports for NIST MCP Server

Generates OSCAL and human-readable reports for gap analysis
and compliance assessments.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

try:
    import aiofiles
except ImportError:
    aiofiles = None

logger = logging.getLogger(__name__)


class OSCALReportGenerator:
    """Generates OSCAL-compliant reports for gap analysis"""

    def __init__(self):
        self.template_path = Path(__file__).parent / "templates"

    def generate_gap_analysis_report(
        self,
        gap_analysis_results: Dict[str, Any],
        organization_info: Optional[Dict[str, Any]] = None,
        assessment_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate OSCAL Assessment Results document from gap analysis"""

        # Default metadata
        org_info = organization_info or {
            "name": "Assessment Organization",
            "identifiers": [],
        }

        assessment_meta = assessment_metadata or {
            "title": "NIST Cybersecurity Framework Gap Analysis",
            "description": "Automated gap analysis assessment",
            "start": datetime.now(timezone.utc).isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
        }

        # Build OSCAL Assessment Results structure
        oscal_report = {
            "assessment-results": {
                "uuid": str(uuid4()),
                "metadata": {
                    "title": assessment_meta.get("title", "Gap Analysis Report"),
                    "description": assessment_meta.get("description", ""),
                    "start": assessment_meta.get(
                        "start", datetime.now(timezone.utc).isoformat()
                    ),
                    "end": assessment_meta.get(
                        "end", datetime.now(timezone.utc).isoformat()
                    ),
                    "version": "1.0.0",
                    "oscal-version": "1.1.2",
                },
                "results": [],
            }
        }

        # Add assessment results based on gap analysis type
        analysis_type = gap_analysis_results.get("analysis_type", "basic")

        if analysis_type == "evidence_based":
            oscal_report["assessment-results"]["results"] = (
                self._build_evidence_based_results(gap_analysis_results)
            )
        else:
            oscal_report["assessment-results"]["results"] = self._build_basic_results(
                gap_analysis_results
            )

        return oscal_report

    def _build_basic_results(self, gap_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build OSCAL results for basic gap analysis"""
        results = []

        # Create result for each missing control
        missing_controls = gap_results.get("missing_controls", {}).get("controls", [])

        for control_id in missing_controls:
            result = {
                "uuid": str(uuid4()),
                "title": f"Gap Analysis Finding for {control_id}",
                "description": f"Control {control_id} is required but not implemented",
                "props": [
                    {"name": "implementation-status", "value": "not-implemented"},
                    {
                        "name": "priority",
                        "value": "high"
                        if control_id
                        in [
                            "AC-1",
                            "AU-1",
                            "CA-1",
                            "CM-1",
                            "CP-1",
                            "IA-1",
                            "IR-1",
                            "PL-1",
                            "RA-1",
                            "SA-1",
                            "SC-1",
                            "SI-1",
                        ]
                        else "medium",
                    },
                ],
                "findings": [
                    {
                        "uuid": str(uuid4()),
                        "title": f"Missing Control {control_id}",
                        "description": f"Control {control_id} is missing from implementation",
                        "target": {
                            "target-id": control_id,
                            "props": [{"name": "control-id", "value": control_id}],
                        },
                    }
                ],
            }
            results.append(result)

        # Add implemented controls with satisfied findings
        family_analysis = gap_results.get("family_analysis", {})
        for family_data in family_analysis.values():
            if family_data.get("implemented", 0) > 0:
                result = {
                    "uuid": str(uuid4()),
                    "title": f"Successfully Implemented Controls in {family_data.get('family', 'Unknown')}",
                    "description": f"{family_data.get('implemented', 0)} controls implemented in this family",
                    "props": [
                        {"name": "implementation-status", "value": "implemented"}
                    ],
                    "findings": [],
                }
                results.append(result)

        return results

    def _build_evidence_based_results(
        self, gap_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build OSCAL results for evidence-based gap analysis"""
        results = []

        # Process each control evaluation
        control_evaluations = gap_results.get("control_evaluation", {})

        for control_id, evaluation in control_evaluations.items():
            status = evaluation.get("status", "unknown")
            confidence = evaluation.get("confidence", 0)

            # Map status to OSCAL finding
            finding = {
                "uuid": str(uuid4()),
                "title": f"Evidence Evaluation for {control_id}",
                "description": evaluation.get(
                    "evaluation_notes", f"Control {control_id} evaluation"
                ),
                "target": {
                    "target-id": control_id,
                    "props": [{"name": "control-id", "value": control_id}],
                },
                "props": [
                    {"name": "evidence-confidence", "value": str(confidence)},
                    {
                        "name": "evidence-count",
                        "value": str(evaluation.get("evidence_count", 0)),
                    },
                ],
            }

            # Add status-specific properties
            if status == "fully_implemented":
                finding["props"].append(
                    {"name": "implementation-status", "value": "fully-implemented"}
                )
            elif status == "partially_implemented":
                finding["props"].append(
                    {"name": "implementation-status", "value": "partially-implemented"}
                )
            else:
                finding["props"].append(
                    {"name": "implementation-status", "value": "not-implemented"}
                )

            result = {
                "uuid": str(uuid4()),
                "title": f"Assessment Result for {control_id}",
                "description": f"Detailed evaluation of control {control_id}",
                "findings": [finding],
                "props": finding["props"],  # Copy props for backward compatibility
            }

            results.append(result)

        return results

    def generate_cmmc_readiness_report(
        self,
        scoring_results: Dict[str, Any],
        organization_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate OSCAL Assessment Results for CMMC readiness scoring"""

        org_info = organization_info or {
            "name": "Assessment Organization",
            "identifiers": [],
        }

        oscal_report = {
            "assessment-results": {
                "uuid": str(uuid4()),
                "metadata": {
                    "title": f"CMMC Level {scoring_results.get('target_level', 2)} Readiness Assessment",
                    "description": "Detailed CMMC readiness scoring by control and domain",
                    "start": datetime.now(timezone.utc).isoformat(),
                    "end": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "oscal-version": "1.1.2",
                    "props": [
                        {"name": "assessment-type", "value": "cmmc-readiness"},
                        {
                            "name": "target-level",
                            "value": str(scoring_results.get("target_level", 2)),
                        },
                        {
                            "name": "overall-maturity-level",
                            "value": str(
                                scoring_results.get("overall_maturity_level", 0)
                            ),
                        },
                        {
                            "name": "overall-confidence-score",
                            "value": str(
                                scoring_results.get("overall_confidence_score", 0)
                            ),
                        },
                    ],
                },
                "results": [],
            }
        }

        # Add domain-level results
        domain_scores = scoring_results.get("domain_scores", {})
        for domain_id, domain_data in domain_scores.items():
            result = {
                "uuid": str(uuid4()),
                "title": f"Domain Assessment: {domain_data.get('description', domain_id)}",
                "description": f"CMMC Domain {domain_id} scoring results",
                "props": [
                    {"name": "domain-id", "value": domain_id},
                    {
                        "name": "domain-maturity-level",
                        "value": str(domain_data.get("maturity_level", 0)),
                    },
                    {
                        "name": "domain-average-score",
                        "value": str(domain_data.get("average_score", 0)),
                    },
                    {
                        "name": "control-count",
                        "value": str(domain_data.get("control_count", 0)),
                    },
                ],
                "findings": [],
            }

            # Add findings for weak controls in this domain
            control_scores = scoring_results.get("control_scores", {})
            for control_id, control_data in control_scores.items():
                if control_id.startswith(domain_id):
                    finding = {
                        "uuid": str(uuid4()),
                        "title": f"Control {control_id} Maturity Assessment",
                        "description": f"Scored at Level {control_data.get('scored_level', 0)} with {control_data.get('confidence_score', 0)}% confidence",
                        "target": {"target-id": control_id},
                        "props": [
                            {
                                "name": "maturity-level",
                                "value": str(control_data.get("scored_level", 0)),
                            },
                            {
                                "name": "confidence-score",
                                "value": str(control_data.get("confidence_score", 0)),
                            },
                        ],
                    }
                    result["findings"].append(finding)

            oscal_report["assessment-results"]["results"].append(result)

        return oscal_report


class HumanReadableReportGenerator:
    """Generates human-readable reports with rich formatting"""

    def __init__(self):
        self.report_templates = {}

    def generate_gap_analysis_report(
        self,
        gap_analysis_results: Dict[str, Any],
        include_recommendations: bool = True,
        include_details: bool = True,
    ) -> str:
        """Generate human-readable gap analysis report"""

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("NIST CYBERSECURITY FRAMEWORK - GAP ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Analysis type and metadata
        analysis_type = gap_analysis_results.get("analysis_type", "basic")
        target_baseline = gap_analysis_results.get("target_baseline", "unknown")

        report_lines.append(f"Analysis Type: {analysis_type.replace('_', ' ').title()}")
        report_lines.append(f"Target Baseline: {target_baseline.title()}")
        report_lines.append(
            "Report Generated: "
            + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        report_lines.append("")

        if analysis_type == "evidence_based":
            # Evidence-based specific sections
            collection_name = gap_analysis_results.get("collection_name", "Unknown")
            compliance_score = gap_analysis_results.get("compliance_score", 0)

            report_lines.append("EVIDENCE-BASED ANALYSIS")
            report_lines.append("-" * 30)
            report_lines.append(f"Evidence Collection: {collection_name}")
            report_lines.append(".1f")
            report_lines.append("")

            # Implementation status breakdown
            impl_status = gap_analysis_results.get("implementation_status", {})
            report_lines.append("IMPLEMENTATION STATUS BREAKDOWN")
            report_lines.append("-" * 35)

            for status_key, status_data in impl_status.items():
                count = status_data.get("count", 0)
                controls = status_data.get("controls", [])
                status_desc = status_key.replace("_", " ").title()
                report_lines.append(
                    f"{status_desc}: {count} control{'s' if count != 1 else ''}"
                )

                if (
                    include_details and len(controls) <= 10
                ):  # Show details if not too many
                    for control in controls[:5]:  # Limit to first 5
                        report_lines.append(f"    • {control}")
                    if len(controls) > 5:
                        report_lines.append(f"    ... and {len(controls) - 5} more")

            report_lines.append("")

            # Family analysis
            family_analysis = gap_analysis_results.get("family_analysis", {})
            if family_analysis:
                report_lines.append("FAMILY ANALYSIS")
                report_lines.append("-" * 15)

                # Sort by implementation percentage (lowest first)
                sorted_families = sorted(
                    family_analysis.items(),
                    key=lambda x: x[1].get("implementation_percentage", 0),
                )

                report_lines.append("<15")
                report_lines.append("-" * 51)
                for family, data in sorted_families:
                    total = data.get("total_controls", 0)
                    impl_pct = data.get("implementation_percentage", 0)
                    avg_conf = data.get("average_confidence", 0)
                    report_lines.append("<15")

                report_lines.append("")

            # Critical gaps
            critical_gaps = gap_analysis_results.get("critical_gaps", [])
            if critical_gaps:
                report_lines.append("CRITICAL GAPS IDENTIFIED")
                report_lines.append("-" * 24)
                for gap in critical_gaps:
                    report_lines.append(f"⚠️  {gap}")
                report_lines.append("")

        else:
            # Basic analysis sections
            compliance_pct = gap_analysis_results.get("compliance_percentage", 0)
            total_required = gap_analysis_results.get("total_required", 0)
            total_implemented = gap_analysis_results.get("total_implemented", 0)

            report_lines.append("COMPLIANCE OVERVIEW")
            report_lines.append("-" * 20)
            report_lines.append(".1f")
            report_lines.append(f"Controls Required: {total_required}")
            report_lines.append(f"Controls Implemented: {total_implemented}")
            report_lines.append("")

            # Missing controls
            missing = gap_analysis_results.get("missing_controls", {})
            if missing.get("count", 0) > 0:
                report_lines.append("MISSING CONTROLS")
                report_lines.append("-" * 16)
                report_lines.append(f"Count: {missing['count']}")

                if include_details:
                    report_lines.append("Controls:")
                    for control in missing.get("controls", [])[
                        :10
                    ]:  # Limit to first 10
                        priority = (
                            " (HIGH)"
                            if control
                            in [
                                "AC-1",
                                "AU-1",
                                "CA-1",
                                "CM-1",
                                "CP-1",
                                "IA-1",
                                "IR-1",
                                "PL-1",
                                "RA-1",
                                "SA-1",
                                "SC-1",
                                "SI-1",
                            ]
                            else ""
                        )
                        report_lines.append(f"    • {control}{priority}")

                    remaining = len(missing.get("controls", [])) - 10
                    if remaining > 0:
                        report_lines.append(f"    ... and {remaining} more")

                report_lines.append("")

        # Recommendations
        if include_recommendations:
            recommendations = gap_analysis_results.get("recommendations", [])
            if recommendations:
                report_lines.append("RECOMMENDATIONS")
                report_lines.append("-" * 15)
                for rec in recommendations:
                    # Add bullet points for better readability
                    if not rec.startswith("•") and not rec.startswith("-"):
                        rec = f"• {rec}"
                    report_lines.append(rec)
                report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("End of Gap Analysis Report")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def generate_cmmc_readiness_report(
        self, scoring_results: Dict[str, Any], include_action_items: bool = True
    ) -> str:
        """Generate human-readable CMMC readiness report"""

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CMMC READINESS ASSESSMENT REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")

        target_level = scoring_results.get("target_level", 2)
        overall_level = scoring_results.get("overall_maturity_level", 0)
        overall_score = scoring_results.get("overall_confidence_score", 0)

        report_lines.append(f"Target CMMC Level: {target_level}")
        report_lines.append(f"Assessment Result: Level {overall_level}")
        report_lines.append(".1f")
        report_lines.append(
            "Report Generated: "
            + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        report_lines.append("")

        # Assessment summary
        status = "ACHIEVED" if overall_level >= target_level else "NOT ACHIEVED"
        report_lines.append("ASSESSMENT SUMMARY")
        report_lines.append("-" * 19)
        report_lines.append(f"Status: {status}")

        if overall_level < target_level:
            gap = target_level - overall_level
            report_lines.append(f"Gap to Target: {gap} level{'s' if gap > 1 else ''}")
        else:
            report_lines.append("Ready for authorization at target level or higher")

        report_lines.append("")

        # Domain breakdown
        domain_scores = scoring_results.get("domain_scores", {})
        report_lines.append("DOMAIN MATURITY SCORES")
        report_lines.append("-" * 23)

        # Sort domains by maturity level (lowest first)
        sorted_domains = sorted(
            domain_scores.items(), key=lambda x: x[1].get("maturity_level", 0)
        )

        report_lines.append(
            f"{'Domain':<20} {'Level':<6} {'Avg Score':<10} {'Max Score':<10} {'Status':<6}"
        )
        report_lines.append("-" * 65)

        for domain_id, domain_data in sorted_domains:
            level = domain_data.get("maturity_level", 0)
            avg_score = domain_data.get("average_score", 0)
            max_score = domain_data.get("max_score", 0)
            desc = domain_data.get("description", domain_id)

            # Determine status indicator
            if level >= target_level:
                status_indicator = "✓"
            elif level >= target_level - 1:
                status_indicator = "~"
            else:
                status_indicator = "✗"

            report_lines.append(
                f"{desc:<20} {level:<6} {avg_score:<10.1f} {max_score:<10.1f} {status_indicator:<6}"
            )

        report_lines.append("")

        # Scoring methodology
        methodology = scoring_results.get("scoring_methodology", {})
        if methodology:
            report_lines.append("SCORING METHODOLOGY")
            report_lines.append("-" * 19)
            for level_key, description in methodology.items():
                report_lines.append(f"Level {level_key}: {description}")
            report_lines.append("")

        # Action items/recommendations
        if include_action_items:
            recommendations = scoring_results.get("recommendations", [])
            if recommendations:
                report_lines.append("ACTION ITEMS AND RECOMMENDATIONS")
                report_lines.append("-" * 35)
                for rec in recommendations:
                    report_lines.append(f"• {rec}")
                report_lines.append("")

        # Control-level details
        control_scores = scoring_results.get("control_scores", {})
        low_confidence_controls = [
            (ctrl_id, data)
            for ctrl_id, data in control_scores.items()
            if data.get("confidence_score", 100)
            < 70  # Show controls with <70% confidence
        ]

        if low_confidence_controls:
            report_lines.append("CONTROLS NEEDING ATTENTION")
            report_lines.append("-" * 28)
            report_lines.append("<12")
            report_lines.append("-" * 50)

            # Sort by lowest confidence first
            low_confidence_controls.sort(key=lambda x: x[1].get("confidence_score", 0))

            for ctrl_id, ctrl_data in low_confidence_controls:
                level = ctrl_data.get("scored_level", 0)
                confidence = ctrl_data.get("confidence_score", 0)
                report_lines.append("<12")

            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("End of CMMC Readiness Report")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)


class ReportManager:
    """Manages report generation and storage"""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/reports")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.oscal_generator = OSCALReportGenerator()
        self.human_generator = HumanReadableReportGenerator()

    def generate_complete_report(
        self,
        gap_results: Optional[Dict[str, Any]] = None,
        cmmc_results: Optional[Dict[str, Any]] = None,
        organization_info: Optional[Dict[str, Any]] = None,
        report_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive report package with all formats"""

        report_id = report_id or str(uuid4())
        timestamp = datetime.now(timezone.utc)

        report_package = {
            "report_id": report_id,
            "generated_at": timestamp.isoformat(),
            "organization": organization_info or {"name": "Default Organization"},
            "reports": {},
        }

        # Generate gap analysis reports
        if gap_results:
            try:
                oscal_gap_report = self.oscal_generator.generate_gap_analysis_report(
                    gap_results, organization_info
                )
                human_gap_report = self.human_generator.generate_gap_analysis_report(
                    gap_results
                )

                report_package["reports"]["gap_analysis"] = {
                    "oscal": oscal_gap_report,
                    "human_readable": human_gap_report,
                    "results": gap_results,
                }
            except Exception as e:
                logger.error(f"Error generating gap analysis reports: {e}")

        # Generate CMMC readiness reports
        if cmmc_results:
            try:
                oscal_cmmc_report = self.oscal_generator.generate_cmmc_readiness_report(
                    cmmc_results, organization_info
                )
                human_cmmc_report = self.human_generator.generate_cmmc_readiness_report(
                    cmmc_results
                )

                report_package["reports"]["cmmc_readiness"] = {
                    "oscal": oscal_cmmc_report,
                    "human_readable": human_cmmc_report,
                    "results": cmmc_results,
                }
            except Exception as e:
                logger.error(f"Error generating CMMC readiness reports: {e}")

        # Save report package
        self._save_report_package(report_package, report_id)

        return report_package

    def generate_oscal_report(
        self,
        results: Dict[str, Any],
        report_type: str,
        organization_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate OSCAL-only report"""

        if report_type == "gap_analysis":
            return self.oscal_generator.generate_gap_analysis_report(
                results, organization_info
            )
        elif report_type == "cmmc_readiness":
            return self.oscal_generator.generate_cmmc_readiness_report(
                results, organization_info
            )
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    def generate_human_report(self, results: Dict[str, Any], report_type: str) -> str:
        """Generate human-readable only report"""

        if report_type == "gap_analysis":
            return self.human_generator.generate_gap_analysis_report(results)
        elif report_type == "cmmc_readiness":
            return self.human_generator.generate_cmmc_readiness_report(results)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    def _save_report_package(
        self, report_package: Dict[str, Any], report_id: str
    ) -> None:
        """Save complete report package to file"""
        try:
            report_file = self.storage_path / f"report_{report_id}.json"

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_package, f, indent=2, default=str)

            logger.info(f"Saved report package: {report_file}")

        except Exception as e:
            logger.error(f"Error saving report package {report_id}: {e}")

    def load_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Load report package from file"""
        try:
            report_file = self.storage_path / f"report_{report_id}.json"

            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Error loading report {report_id}: {e}")
            return None

    def list_reports(self) -> List[Dict[str, Any]]:
        """List available reports with metadata"""
        reports = []

        try:
            for report_file in self.storage_path.glob("report_*.json"):
                try:
                    with open(report_file, "r", encoding="utf-8") as f:
                        report_data = json.load(f)
                        reports.append(
                            {
                                "report_id": report_data.get("report_id", "unknown"),
                                "generated_at": report_data.get(
                                    "generated_at", "unknown"
                                ),
                                "organization": report_data.get("organization", {}).get(
                                    "name", "unknown"
                                ),
                                "report_types": list(
                                    report_data.get("reports", {}).keys()
                                ),
                                "file_path": str(report_file),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error reading report file {report_file}: {e}")
        except Exception as e:
            logger.error(f"Error listing reports: {e}")

        return reports


# Global report manager instance
report_manager = ReportManager()
