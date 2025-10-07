"""Advanced Analysis Tools for NIST MCP Server

Provides sophisticated analysis capabilities for cybersecurity frameworks.
"""

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class NISTAnalysisTools:
    """Advanced analysis tools for NIST frameworks"""

    def __init__(self, data_loader: Any):
        self.data_loader = data_loader

    async def gap_analysis(
        self,
        implemented_controls: list[str],
        target_baseline: str = "moderate",
        evidence_collection_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform gap analysis between implemented controls and target baseline

        If evidence_collection_id is provided, performs evidence-based evaluation
        against control definitions rather than simple ID matching.

        Args:
            implemented_controls: List of implemented control IDs
            target_baseline: Target baseline ("low", "moderate", "high")
            evidence_collection_id: ID of evidence collection for evaluation
        """
        try:
            # Load baseline controls
            import sys
            from pathlib import Path

            sys.path.append(str(Path(__file__).parent.parent.parent))
            from tools.control_tools import ControlTools

            tools = ControlTools(self.data_loader)
            baseline_data = await tools.get_control_baselines(target_baseline)
            baseline_controls = {ctrl["id"] for ctrl in baseline_data["controls"]}

            implemented_set = set(implemented_controls)

            # If evidence collection provided, perform detailed evidence evaluation
            if evidence_collection_id:
                return await self._evidence_based_gap_analysis(
                    implemented_controls,
                    baseline_controls,
                    evidence_collection_id,
                    target_baseline,
                )

            # Basic gap analysis (ID-based)
            return await self._basic_gap_analysis(
                implemented_controls, baseline_controls, target_baseline
            )

        except Exception as e:
            logger.error(f"Error performing gap analysis: {e}")
            raise

    async def _basic_gap_analysis(
        self,
        implemented_controls: list[str],
        baseline_controls: set[str],
        target_baseline: str,
    ) -> dict[str, Any]:
        """Perform basic gap analysis by comparing control IDs"""
        implemented_set = set(implemented_controls)

        # Calculate gaps
        missing_controls = baseline_controls - implemented_set
        extra_controls = implemented_set - baseline_controls
        compliant_controls = implemented_set & baseline_controls

        # Analyze by family
        family_analysis: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"required": 0, "implemented": 0, "missing": []}
        )

        for control_id in baseline_controls:
            family = control_id[:2]
            family_analysis[family]["required"] += 1
            if control_id in implemented_set:
                family_analysis[family]["implemented"] += 1
            else:
                family_analysis[family]["missing"].append(control_id)

        # Calculate compliance percentage
        compliance_percentage = (
            (len(compliant_controls) / len(baseline_controls)) * 100
            if baseline_controls
            else 0
        )

        return {
            "analysis_type": "basic",
            "target_baseline": target_baseline,
            "compliance_percentage": round(compliance_percentage, 2),
            "total_required": len(baseline_controls),
            "total_implemented": len(implemented_set),
            "compliant_controls": len(compliant_controls),
            "missing_controls": {
                "count": len(missing_controls),
                "controls": sorted(list(missing_controls)),
            },
            "extra_controls": {
                "count": len(extra_controls),
                "controls": sorted(list(extra_controls)),
            },
            "family_analysis": dict(family_analysis),
            "recommendations": self._generate_gap_recommendations(
                family_analysis, missing_controls
            ),
        }

    async def _evidence_based_gap_analysis(
        self,
        implemented_controls: list[str],
        baseline_controls: set[str],
        evidence_collection_id: str,
        target_baseline: str,
    ) -> dict[str, Any]:
        """Perform evidence-based gap analysis by evaluating evidence against control definitions"""
        try:
            from .evidence import evidence_manager

            evidence_collection = evidence_manager.collections.get(
                evidence_collection_id
            )
            if not evidence_collection:
                raise ValueError(
                    f"Evidence collection {evidence_collection_id} not found"
                )

            # Evaluate each baseline control against evidence
            evidence_evaluation = {}

            for control_id in baseline_controls:
                control_evaluation = await self._evaluate_control_evidence(
                    control_id, evidence_collection
                )
                evidence_evaluation[control_id] = control_evaluation

            # Categorize controls by implementation status
            fully_implemented = []
            partially_implemented = []
            not_implemented = []
            unknown_status = []

            for control_id, evaluation in evidence_evaluation.items():
                if evaluation["status"] == "fully_implemented":
                    fully_implemented.append(control_id)
                elif evaluation["status"] == "partially_implemented":
                    partially_implemented.append(control_id)
                elif evaluation["status"] == "not_implemented":
                    not_implemented.append(control_id)
                else:
                    unknown_status.append(control_id)

            # Calculate compliance metrics
            total_required = len(baseline_controls)
            total_implemented = len(fully_implemented) + len(partially_implemented)

            # Weighted compliance (partial gets 0.5, full gets 1.0)
            compliance_score = (
                (len(fully_implemented) + 0.5 * len(partially_implemented))
                / total_required
                * 100
            )

            # Family analysis
            family_analysis = self._analyze_evidence_by_family(
                evidence_evaluation, baseline_controls
            )

            # Remediation priorities
            remediation_priorities = self._prioritize_remediation(
                evidence_evaluation, not_implemented, partially_implemented
            )

            return {
                "analysis_type": "evidence_based",
                "target_baseline": target_baseline,
                "evidence_collection": evidence_collection_id,
                "collection_name": evidence_collection.name,
                "compliance_score": round(compliance_score, 2),
                "control_evaluation": evidence_evaluation,
                "implementation_status": {
                    "fully_implemented": {
                        "count": len(fully_implemented),
                        "controls": fully_implemented,
                    },
                    "partially_implemented": {
                        "count": len(partially_implemented),
                        "controls": partially_implemented,
                    },
                    "not_implemented": {
                        "count": len(not_implemented),
                        "controls": not_implemented,
                    },
                    "unknown_status": {
                        "count": len(unknown_status),
                        "controls": unknown_status,
                    },
                },
                "family_analysis": family_analysis,
                "remediation_priorities": remediation_priorities,
                "total_required": total_required,
                "total_with_evidence": total_implemented,
                "recommendations": self._generate_evidence_based_recommendations(
                    evidence_evaluation
                ),
                "critical_gaps": self._identify_critical_evidence_gaps(
                    evidence_evaluation
                ),
            }

        except Exception as e:
            logger.error(f"Error in evidence-based gap analysis: {e}")
            raise

    async def risk_assessment_helper(self, control_ids: list[str]) -> dict[str, Any]:
        """Help assess risk coverage based on control selection"""
        try:
            controls_data = await self.data_loader.load_controls()

            # Analyze control coverage by security objective
            security_objectives: dict[str, list[str]] = {
                "confidentiality": [],
                "integrity": [],
                "availability": [],
            }

            # Risk categories based on control families
            risk_categories = {
                "access_control": ["AC"],
                "audit_accountability": ["AU"],
                "configuration_management": ["CM"],
                "contingency_planning": ["CP"],
                "identification_authentication": ["IA"],
                "incident_response": ["IR"],
                "maintenance": ["MA"],
                "media_protection": ["MP"],
                "physical_environmental": ["PE"],
                "planning": ["PL"],
                "personnel_security": ["PS"],
                "risk_assessment": ["RA"],
                "system_communications": ["SC"],
                "system_integrity": ["SI"],
                "system_acquisition": ["SA"],
                "assessment_authorization": ["CA"],
                "awareness_training": ["AT"],
                "program_management": ["PM"],
            }

            coverage_analysis: dict[str, dict[str, Any]] = {}
            for category, families in risk_categories.items():
                covered_families = set()
                control_count = 0

                for control_id in control_ids:
                    family = control_id[:2]
                    if family in families:
                        covered_families.add(family)
                        control_count += 1

                coverage_analysis[category] = {
                    "families_covered": list(covered_families),
                    "control_count": control_count,
                    "coverage_percentage": (
                        round((len(covered_families) / len(families)) * 100, 2)
                        if families
                        else 0
                    ),
                }

            # Overall risk coverage score
            total_categories = len(risk_categories)
            covered_categories = sum(
                1
                for cat in coverage_analysis.values()
                if cat.get("control_count", 0) > 0  # type: ignore[operator]
            )
            overall_coverage = round((covered_categories / total_categories) * 100, 2)

            return {
                "overall_risk_coverage": overall_coverage,
                "total_controls_analyzed": len(control_ids),
                "risk_category_coverage": coverage_analysis,
                "recommendations": self._generate_risk_recommendations(
                    coverage_analysis
                ),
                "high_priority_gaps": self._identify_critical_gaps(coverage_analysis),
            }
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            raise

    async def compliance_mapping(
        self, framework: str, control_ids: list[str]
    ) -> dict[str, Any]:
        """Map controls to compliance frameworks (SOC2, ISO27001, etc.)"""
        try:
            # Simplified compliance mappings - in production, load from comprehensive mapping files
            compliance_mappings = {
                "soc2": {
                    "CC6.1": ["AC-1", "AC-2", "AC-3", "AC-5", "AC-6"],
                    "CC6.2": ["AC-7", "AC-8", "AC-11", "AC-12"],
                    "CC6.3": ["AC-17", "AC-18", "AC-19", "AC-20"],
                    "CC7.1": ["AU-1", "AU-2", "AU-3", "AU-6", "AU-12"],
                    "CC7.2": ["AU-4", "AU-5", "AU-9", "AU-11"],
                    "CC8.1": ["CM-1", "CM-2", "CM-3", "CM-5", "CM-6"],
                },
                "iso27001": {
                    "A.9.1.1": ["AC-1", "AC-2"],
                    "A.9.1.2": ["AC-3", "AC-5", "AC-6"],
                    "A.9.2.1": ["AC-7", "AC-8"],
                    "A.12.4.1": ["AU-1", "AU-2", "AU-3"],
                    "A.12.4.2": ["AU-6", "AU-12"],
                    "A.12.6.1": ["CM-1", "CM-2", "CM-3"],
                },
            }

            if framework.lower() not in compliance_mappings:
                return {
                    "error": f"Framework '{framework}' not supported",
                    "supported_frameworks": list(compliance_mappings.keys()),
                }

            framework_map = compliance_mappings[framework.lower()]

            # Analyze coverage
            covered_requirements = {}
            uncovered_requirements = {}

            for requirement, required_controls in framework_map.items():
                covered_controls = [
                    ctrl for ctrl in required_controls if ctrl in control_ids
                ]
                coverage_percentage = (
                    len(covered_controls) / len(required_controls)
                ) * 100

                if coverage_percentage > 0:
                    covered_requirements[requirement] = {
                        "covered_controls": covered_controls,
                        "total_required": len(required_controls),
                        "coverage_percentage": round(coverage_percentage, 2),
                    }
                else:
                    uncovered_requirements[requirement] = {
                        "required_controls": required_controls,
                        "total_required": len(required_controls),
                    }

            overall_compliance = round(
                (len(covered_requirements) / len(framework_map)) * 100, 2
            )

            return {
                "framework": framework.upper(),
                "overall_compliance_percentage": overall_compliance,
                "total_requirements": len(framework_map),
                "covered_requirements": len(covered_requirements),
                "uncovered_requirements": len(uncovered_requirements),
                "requirement_details": {
                    "covered": covered_requirements,
                    "uncovered": uncovered_requirements,
                },
                "recommendations": self._generate_compliance_recommendations(
                    uncovered_requirements
                ),
            }
        except Exception as e:
            logger.error(f"Error in compliance mapping: {e}")
            raise

    async def control_relationships(self, control_id: str) -> dict[str, Any]:
        """Analyze relationships and dependencies between controls"""
        try:
            controls_data = await self.data_loader.load_controls()
            control = self.data_loader.get_control_by_id(controls_data, control_id)

            if not control:
                raise ValueError(f"Control {control_id} not found")

            # Find related controls
            related_controls = self._find_related_controls(control, controls_data)

            # Find control enhancements
            enhancements = []
            all_controls = controls_data.get("catalog", {}).get("controls", [])

            for ctrl in all_controls:
                ctrl_id = ctrl.get("id", "")
                if ctrl_id.startswith(f"{control_id}(") and "(" in ctrl_id:
                    enhancements.append(
                        {
                            "id": ctrl_id,
                            "title": ctrl.get("title", ""),
                            "enhancement_number": ctrl_id.split("(")[1].split(")")[0],
                        }
                    )

            # Find controls that reference this one
            referencing_controls = self._find_referencing_controls(
                control_id, controls_data
            )

            return {
                "control_id": control_id,
                "control_title": control.get("title", ""),
                "family": control_id[:2],
                "enhancements": {"count": len(enhancements), "details": enhancements},
                "related_controls": related_controls,
                "referencing_controls": referencing_controls,
                "implementation_guidance": self._extract_implementation_guidance(
                    control
                ),
            }
        except Exception as e:
            logger.error(f"Error analyzing control relationships: {e}")
            raise

    def _generate_gap_recommendations(
        self, family_analysis: dict, missing_controls: set[str]
    ) -> list[str]:
        """Generate recommendations based on gap analysis"""
        recommendations = []

        # Identify families with low coverage
        for family, data in family_analysis.items():
            if data["required"] > 0:
                coverage = (data["implemented"] / data["required"]) * 100
                if coverage < 50:
                    recommendations.append(
                        f"Priority: Implement {family} family controls - only {coverage:.1f}% coverage"
                    )
                elif coverage < 80:
                    recommendations.append(
                        f"Improve {family} family controls - {coverage:.1f}% coverage"
                    )

        # Highlight critical missing controls
        critical_controls = {
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
        }
        missing_critical = missing_controls & critical_controls

        if missing_critical:
            recommendations.insert(
                0,
                f"CRITICAL: Implement foundational controls: {', '.join(sorted(missing_critical))}",
            )

        return recommendations

    def _generate_risk_recommendations(self, coverage_analysis: dict) -> list[str]:
        """Generate risk-based recommendations"""
        recommendations = []

        # Identify high-risk gaps
        high_risk_categories = {
            "access_control": "Implement access control measures to prevent unauthorized access",
            "incident_response": "Establish incident response capabilities for security events",
            "system_integrity": "Implement system integrity controls to detect unauthorized changes",
        }

        for category, message in high_risk_categories.items():
            if coverage_analysis.get(category, {}).get("control_count", 0) == 0:
                recommendations.append(f"HIGH RISK: {message}")

        return recommendations

    def _generate_compliance_recommendations(
        self, uncovered_requirements: dict
    ) -> list[str]:
        """Generate compliance-focused recommendations"""
        recommendations = []

        if uncovered_requirements:
            recommendations.append(
                "Implement missing controls to achieve full compliance"
            )

            # Prioritize by number of required controls
            sorted_reqs = sorted(
                uncovered_requirements.items(),
                key=lambda x: x[1]["total_required"],
                reverse=True,
            )

            for req, data in sorted_reqs[:3]:  # Top 3 gaps
                recommendations.append(
                    f"Priority requirement {req}: {len(data['required_controls'])} controls needed"
                )

        return recommendations

    def _find_related_controls(
        self, control: dict, controls_data: dict
    ) -> list[dict[str, Any]]:
        """Find controls related to the given control"""
        related = []
        control_family = control.get("id", "")[:2]

        # Find other controls in the same family
        all_controls = controls_data.get("catalog", {}).get("controls", [])
        for ctrl in all_controls:
            ctrl_id = ctrl.get("id", "")
            if ctrl_id.startswith(control_family) and ctrl_id != control.get("id", ""):
                if "(" not in ctrl_id:  # Exclude enhancements
                    related.append(
                        {
                            "id": ctrl_id,
                            "title": ctrl.get("title", ""),
                            "relationship": "same_family",
                        }
                    )

        return related[:5]  # Limit to 5 related controls

    def _find_referencing_controls(
        self, control_id: str, controls_data: dict
    ) -> list[dict[str, Any]]:
        """Find controls that reference the given control"""
        referencing = []
        all_controls = controls_data.get("catalog", {}).get("controls", [])

        for ctrl in all_controls:
            # Check if control text mentions the target control
            ctrl_text = str(ctrl).lower()
            if control_id.lower() in ctrl_text and ctrl.get("id", "") != control_id:
                referencing.append(
                    {
                        "id": ctrl.get("id", ""),
                        "title": ctrl.get("title", ""),
                        "relationship": "references",
                    }
                )

        return referencing[:3]  # Limit to 3 referencing controls

    def _extract_implementation_guidance(self, control: dict) -> list[str]:
        """Extract implementation guidance from control"""
        guidance = []

        parts = control.get("parts", [])
        for part in parts:
            if part.get("name") == "guidance":
                prose = part.get("prose", "")
                if prose:
                    # Split into sentences and take first few
                    sentences = prose.split(". ")
                    guidance.extend(sentences[:3])

        return guidance

    def _identify_critical_gaps(self, coverage_analysis: dict) -> list[str]:
        """Identify critical security gaps"""
        critical_gaps = []

        # Define critical categories
        critical_categories = [
            "access_control",
            "incident_response",
            "system_integrity",
            "audit_accountability",
        ]

        for category in critical_categories:
            if coverage_analysis.get(category, {}).get("control_count", 0) == 0:
                critical_gaps.append(category.replace("_", " ").title())

        return critical_gaps

    async def _evaluate_control_evidence(
        self, control_id: str, evidence_collection: Any
    ) -> dict[str, Any]:
        """Evaluate evidence for a specific control against its definition"""
        try:
            # Load control definition
            controls_data = await self.data_loader.load_controls()
            control = self.data_loader.get_control_by_id(controls_data, control_id)

            if not control:
                return {
                    "status": "unknown",
                    "confidence": 0,
                    "evidence_count": 0,
                    "evaluation_notes": f"Control {control_id} not found in catalog",
                    "gaps": ["Control definition not available"],
                }

            # Get relevant evidence
            evidence_items = evidence_collection.get_evidence_for_control(control_id)
            approved_evidence = [
                e for e in evidence_items if e.status.value == "approved"
            ]

            if not approved_evidence:
                return {
                    "status": "no_evidence",
                    "confidence": 0,
                    "evidence_count": len(evidence_items),
                    "evaluation_notes": "No approved evidence found",
                    "gaps": ["Missing evidence for control implementation"],
                }

            # Evaluate evidence against control requirements
            control_requirements = self._extract_control_requirements(control)
            evidence_coverage = self._evaluate_evidence_coverage(
                control_requirements, approved_evidence
            )

            # Determine implementation status
            coverage_score = evidence_coverage["coverage_percentage"] / 100.0

            if coverage_score >= 0.8:  # 80%+ coverage = fully implemented
                status = "fully_implemented"
            elif coverage_score >= 0.5:  # 50-79% coverage = partially implemented
                status = "partially_implemented"
            else:
                status = "not_implemented"

            return {
                "status": status,
                "confidence": coverage_score,
                "evidence_count": len(approved_evidence),
                "total_evidence_items": len(evidence_items),
                "coverage": evidence_coverage,
                "requirements_mapped": evidence_coverage["covered_requirements"],
                "gaps": evidence_coverage["uncovered_requirements"],
                "evaluation_notes": f"Evidence covers {coverage_score:.0%} of control requirements",
            }

        except Exception as e:
            logger.error(f"Error evaluating evidence for control {control_id}: {e}")
            return {"status": "error", "confidence": 0, "error": str(e)}

    def _extract_control_requirements(self, control: dict) -> list[str]:
        """Extract key requirements from control definition"""
        requirements = []

        # Extract from control parts (guidance, discussion, etc.)
        parts = control.get("parts", [])
        for part in parts:
            if part.get("name") in ["statement", "guidance", "discussion"]:
                prose = part.get("prose", "")
                if prose:
                    # Break into meaningful requirements (sentences)
                    sentences = [s.strip() for s in prose.split(".") if s.strip()]
                    requirements.extend(sentences)

        # Extract from properties
        properties = control.get("props", [])
        for prop in properties:
            if prop.get("name") in ["requirement", "implementation"]:
                value = prop.get("value", "")
                if value:
                    requirements.append(value)

        # Fallback to title-based requirements
        if not requirements:
            title = control.get("title", "")
            if title:
                requirements.append(f"Implement {title.lower()}")

        return requirements[:10]  # Limit to avoid overload

    def _evaluate_evidence_coverage(
        self, requirements: list[str], evidence_items: list
    ) -> dict[str, Any]:
        """Evaluate how well evidence covers control requirements"""
        covered_requirements = []
        uncovered_requirements = []

        for req in requirements:
            req_lower = req.lower()
            covered = False

            # Check if any evidence addresses this requirement
            for evidence in evidence_items:
                evidence_content = ""
                if isinstance(evidence.content, str):
                    evidence_content = evidence.content.lower()
                elif isinstance(evidence.content, dict):
                    evidence_content = str(evidence.content).lower()

                evidence_desc = evidence.description.lower()

                # Check for relevant keywords/artifacts
                if any(
                    keyword in req_lower
                    for keyword in [
                        "policy",
                        "procedure",
                        "access",
                        "log",
                        "audit",
                        "monitor",
                        "control",
                        "implement",
                        "document",
                        "test",
                        "review",
                        "approve",
                    ]
                ) and any(
                    keyword in (evidence_content + evidence_desc)
                    for keyword in [
                        "policy",
                        "procedure",
                        evidence.evidence_type.value.replace("_", " "),
                        "document",
                        "test",
                        "review",
                        "log",
                        "configuration",
                        "tool",
                    ]
                ):
                    covered = True
                    break

            if covered:
                covered_requirements.append(req)
            else:
                uncovered_requirements.append(req)

        coverage_percentage = (
            len(covered_requirements) / len(requirements) * 100 if requirements else 0
        )

        return {
            "total_requirements": len(requirements),
            "covered_requirements": len(covered_requirements),
            "uncovered_requirements": len(uncovered_requirements),
            "coverage_percentage": round(coverage_percentage, 2),
            "details": {
                "covered": covered_requirements,
                "uncovered": uncovered_requirements,
            },
        }

    def _analyze_evidence_by_family(
        self, evidence_evaluation: dict, baseline_controls: set
    ) -> dict[str, Any]:
        """Analyze evidence coverage by control family"""
        family_analysis = defaultdict(
            lambda: {
                "total_controls": 0,
                "fully_implemented": 0,
                "partially_implemented": 0,
                "not_implemented": 0,
                "no_evidence": 0,
                "average_confidence": 0,
                "controls": [],
            }
        )

        for control_id in baseline_controls:
            family = control_id[:2]
            eval_data = evidence_evaluation.get(
                control_id, {"status": "unknown", "confidence": 0}
            )

            family_analysis[family]["total_controls"] += 1
            family_analysis[family]["controls"].append(
                {
                    "id": control_id,
                    "status": eval_data.get("status", "unknown"),
                    "confidence": eval_data.get("confidence", 0),
                }
            )

            status = eval_data.get("status", "unknown")
            if status in [
                "fully_implemented",
                "partially_implemented",
                "not_implemented",
                "no_evidence",
            ]:
                family_analysis[family][status] += 1

        # Calculate averages and percentages
        for family, data in family_analysis.items():
            total = data["total_controls"]
            if total > 0:
                confidences = [c["confidence"] for c in data["controls"]]
                data["average_confidence"] = round(
                    sum(confidences) / len(confidences), 2
                )

                data["implementation_percentage"] = round(
                    (data["fully_implemented"] + data["partially_implemented"])
                    / total
                    * 100,
                    2,
                )

        return dict(family_analysis)

    def _prioritize_remediation(
        self,
        evidence_evaluation: dict,
        not_implemented: list,
        partially_implemented: list,
    ) -> list[dict[str, Any]]:
        """Prioritize remediation efforts based on evidence gaps"""
        priorities = []

        # Critical controls that should be prioritized
        critical_controls = {
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
        }

        # High priority: critical controls not implemented
        for control_id in not_implemented:
            if control_id in critical_controls:
                eval_data = evidence_evaluation.get(control_id, {})
                priorities.append(
                    {
                        "priority": "critical",
                        "control_id": control_id,
                        "action": "urgent_implementation",
                        "reason": "Critical foundational control with no evidence of implementation",
                        "gaps": eval_data.get("gaps", []),
                    }
                )

        # High priority: critical controls partially implemented
        for control_id in partially_implemented:
            if control_id in critical_controls:
                eval_data = evidence_evaluation.get(control_id, {})
                priorities.append(
                    {
                        "priority": "high",
                        "control_id": control_id,
                        "action": "enhance_implementation",
                        "reason": "Critical control with incomplete evidence",
                        "gaps": eval_data.get("gaps", []),
                    }
                )

        # Medium priority: other not implemented controls
        for control_id in not_implemented:
            if control_id not in critical_controls:
                eval_data = evidence_evaluation.get(control_id, {})
                priorities.append(
                    {
                        "priority": "medium",
                        "control_id": control_id,
                        "action": "implement",
                        "reason": "Required control not implemented",
                        "gaps": eval_data.get("gaps", []),
                    }
                )

        # Low priority: partially implemented controls needing enhancement
        for control_id in partially_implemented:
            if control_id not in critical_controls:
                eval_data = evidence_evaluation.get(control_id, {})
                priorities.append(
                    {
                        "priority": "low",
                        "control_id": control_id,
                        "action": "enhance",
                        "reason": "Control needs additional evidence",
                        "gaps": eval_data.get("gaps", []),
                    }
                )

        return priorities

    def _generate_evidence_based_recommendations(
        self, evidence_evaluation: dict
    ) -> list[str]:
        """Generate recommendations based on evidence evaluation"""
        recommendations = []

        # Analyze overall status
        status_counts = {}
        for eval_data in evidence_evaluation.values():
            status = eval_data.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        fully_implemented = status_counts.get("fully_implemented", 0)
        partially_implemented = status_counts.get("partially_implemented", 0)
        not_implemented = status_counts.get("not_implemented", 0)
        no_evidence = status_counts.get("no_evidence", 0)
        total = sum(status_counts.values())

        if total > 0:
            full_pct = fully_implemented / total * 100
            partial_pct = partially_implemented / total * 100
            not_impl_pct = not_implemented / total * 100

            recommendations.append(
                f"Overall compliance: {full_pct:.1f}% fully implemented, "
                f"{partial_pct:.1f}% partially implemented, {not_impl_pct:.1f}% not implemented"
            )

        # Evidence quality recommendations
        approved_evidence_total = sum(
            e.get("evidence_count", 0) for e in evidence_evaluation.values()
        )
        if approved_evidence_total < len(evidence_evaluation) * 2:
            recommendations.append(
                "INCREASE EVIDENCE: Consider adding more evidence types per control (policy + procedure + test results)"
            )

        # Critical gaps
        critical_missing = []
        for control_id, eval_data in evidence_evaluation.items():
            if eval_data.get("status") in ["not_implemented", "no_evidence"]:
                family = control_id[:2]
                if family in [
                    "AC",
                    "AU",
                    "CA",
                    "CM",
                    "IA",
                    "IR",
                    "PL",
                    "RA",
                    "SA",
                    "SC",
                    "SI",
                ]:
                    critical_missing.append(control_id)

        if critical_missing:
            recommendations.append(
                f"PRIORITY FOCUS: Implement critical controls: {', '.join(critical_missing[:5])}{'...' if len(critical_missing) > 5 else ''}"
            )

        # Status improvements
        if no_evidence > 0:
            recommendations.append(
                f"COLLECT EVIDENCE: {no_evidence} controls have no approved evidence - start evidence collection process"
            )

        return recommendations

    def _identify_critical_evidence_gaps(self, evidence_evaluation: dict) -> list[str]:
        """Identify critical gaps based on evidence evaluation"""
        critical_gaps = []

        # Check for critical families with low implementation
        family_status = defaultdict(list)
        for control_id, eval_data in evidence_evaluation.items():
            family = control_id[:2]
            status = eval_data.get("status", "unknown")
            if status in ["fully_implemented", "partially_implemented"]:
                family_status[family].append(True)
            else:
                family_status[family].append(False)

        critical_families = {
            "AC": "Access Control",
            "AU": "Audit and Accountability",
            "CA": "Assessment, Authorization, and Monitoring",
            "CM": "Configuration Management",
            "IA": "Identification and Authentication",
            "IR": "Incident Response",
            "SC": "System and Communications Protection",
            "SI": "System and Information Integrity",
        }

        for family, status_list in family_status.items():
            if family in critical_families:
                implemented_count = sum(1 for s in status_list if s)
                total_count = len(status_list)
                coverage = implemented_count / total_count if total_count > 0 else 0

                if coverage < 0.5:  # Less than 50% coverage
                    critical_gaps.append(
                        f"{critical_families[family]} family critically under-implemented "
                        f"({coverage:.0%} coverage)"
                    )

        return critical_gaps

    async def cmmc_readiness_scoring(
        self, evidence_collection_id: str, target_level: int = 2
    ) -> dict[str, Any]:
        """Generate CMMC Level 1-3 readiness scores per control/domain

        Args:
            evidence_collection_id: ID of evidence collection to evaluate
            target_level: Target CMMC level (1-3)
        """
        try:
            from .evidence import evidence_manager

            evidence_collection = evidence_manager.collections.get(
                evidence_collection_id
            )
            if not evidence_collection:
                raise ValueError(
                    f"Evidence collection {evidence_collection_id} not found"
                )

            # Get CMMC controls for target level
            cmmc_data = await self.data_loader.load_cmmc_framework()
            level_controls = []

            for level_data in cmmc_data.get("framework", {}).get("levels", []):
                if level_data.get("level") <= target_level:
                    level_controls.extend(level_data.get("controls", []))

            # Remove duplicates while preserving order
            level_controls = list(dict.fromkeys(level_controls))

            # Evaluate each CMMC control
            control_scores = {}
            domain_scores = defaultdict(list)

            for control_id in level_controls:
                evaluation = await self._evaluate_control_evidence(
                    control_id, evidence_collection
                )
                confidence_score = (
                    evaluation.get("confidence", 0) * 100
                )  # Convert to percentage

                # Map to maturity levels (simplified)
                if confidence_score >= 80:
                    maturity_level = 3  # Fully implemented and evidenced
                elif confidence_score >= 60:
                    maturity_level = 2  # Partially implemented
                elif confidence_score >= 40:
                    maturity_level = 1  # Basic implementation
                else:
                    maturity_level = 0  # Not implemented

                control_scores[control_id] = {
                    "scored_level": min(target_level, maturity_level),
                    "confidence_score": round(confidence_score, 1),
                    "target_level": target_level,
                    "evidence_status": evaluation.get("status", "unknown"),
                    "gaps": evaluation.get("gaps", []),
                }

                # Group by domain (first 2 characters)
                domain = control_id[:2]
                domain_scores[domain].append(maturity_level)

            # Calculate domain and overall scores
            domain_summary = {}
            domain_weight = {}

            for domain, scores in domain_scores.items():
                avg_score = sum(scores) / len(scores)
                min_score = min(scores)  # Domain score is limited by weakest control
                max_score = max(scores)

                # Weight by number of controls in domain
                weight = len(scores)
                domain_weight[domain] = weight

                domain_summary[domain] = {
                    "average_score": round(avg_score, 2),
                    "min_score": min_score,
                    "max_score": max_score,
                    "control_count": weight,
                    "maturity_level": min(
                        target_level, int(min_score)
                    ),  # Domain level limited by min
                    "description": self._get_domain_description(domain),
                }

            # Overall organization score (weighted average of domain minimums)
            total_weight = sum(domain_weight.values())
            weighted_score = (
                sum(
                    domain_summary[d]["min_score"] * domain_weight[d]
                    for d in domain_weight
                )
                / total_weight
            )
            overall_maturity_level = min(target_level, int(weighted_score))

            return {
                "target_level": target_level,
                "overall_maturity_level": overall_maturity_level,
                "overall_confidence_score": round(weighted_score, 2),
                "control_scores": control_scores,
                "domain_scores": dict(domain_summary),
                "scoring_methodology": {
                    "level_0": "Not implemented (<40% confidence)",
                    "level_1": "Basic implementation (40-59% confidence)",
                    "level_2": "Partial/functional implementation (60-79% confidence)",
                    "level_3": "Full implementation with evidence (≥80% confidence)",
                },
                "recommendations": self._generate_cmmc_improvement_recommendations(
                    domain_summary, control_scores
                ),
            }

        except Exception as e:
            logger.error(f"Error generating CMMC readiness score: {e}")
            raise

    def _get_domain_description(self, domain: str) -> str:
        """Get domain description for CMMC reporting"""
        descriptions = {
            "AC": "Access Control",
            "AT": "Awareness and Training",
            "AU": "Audit and Accountability",
            "CA": "Assessment and Authorization",
            "CM": "Configuration Management",
            "CP": "Contingency Planning",
            "IA": "Identification and Authentication",
            "IR": "Incident Response",
            "MP": "Media Protection",
            "PE": "Physical and Environmental Protection",
            "PL": "Planning",
            "PS": "Personnel Security",
            "RA": "Risk Assessment",
            "RE": "Recovery",
            "RC": "Recovery Planning",
            "RP": "Response Planning",
            "SA": "System and Services Acquisition",
            "SC": "System and Communications Protection",
            "SI": "System and Information Integrity",
            "SR": "Supply Chain Risk Management",
        }
        return descriptions.get(domain, f"Domain {domain}")

    def _generate_cmmc_improvement_recommendations(
        self, domain_scores: dict, control_scores: dict
    ) -> list[str]:
        """Generate CMMC-specific improvement recommendations"""
        recommendations = []

        # Find domains below target maturity
        weak_domains = []
        for domain, data in domain_scores.items():
            if data["maturity_level"] < data.get("target_level", 2):
                weak_domains.append((domain, data["maturity_level"]))

        weak_domains.sort(key=lambda x: x[1])  # Sort by lowest maturity first

        if weak_domains:
            recommendations.append(
                "FOCUS AREAS: Improve domains with low maturity scores:"
            )
            for domain, level in weak_domains[:3]:  # Top 3 weakest domains
                domain_name = self._get_domain_description(domain)
                recommendations.append(f"  • {domain_name} (current level: {level})")

        # Find controls needing immediate attention (<60% confidence)
        weak_controls = []
        for control_id, score_data in control_scores.items():
            if score_data["confidence_score"] < 60:
                weak_controls.append((control_id, score_data["confidence_score"]))

        weak_controls.sort(key=lambda x: x[1])  # Lowest confidence first

        if weak_controls:
            recommendations.append(
                "CRITICAL CONTROLS: Address controls with low confidence scores:"
            )
            for control_id, confidence in weak_controls[:5]:  # Top 5 weakest controls
                recommendations.append(
                    f"  • {control_id} ({confidence:.1f}% confidence)"
                )

        # Evidence quality recommendations
        low_evidence_count = sum(
            1 for s in control_scores.values() if s["confidence_score"] < 40
        )
        if low_evidence_count > 0:
            recommendations.append(
                f"EVIDENCE GAP: {low_evidence_count} controls lack sufficient evidence"
            )

        return recommendations
