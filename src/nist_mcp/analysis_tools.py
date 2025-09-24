"""
Advanced Analysis Tools for NIST MCP Server

Provides sophisticated analysis capabilities for cybersecurity frameworks.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class NISTAnalysisTools:
    """Advanced analysis tools for NIST frameworks"""

    def __init__(self, data_loader: Any):
        self.data_loader = data_loader

    async def gap_analysis(self, implemented_controls: List[str], target_baseline: str = "moderate") -> Dict[str, Any]:
        """Perform gap analysis between implemented controls and target baseline"""
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
            
            # Calculate gaps
            missing_controls = baseline_controls - implemented_set
            extra_controls = implemented_set - baseline_controls
            compliant_controls = implemented_set & baseline_controls
            
            # Analyze by family
            family_analysis = defaultdict(lambda: {"required": 0, "implemented": 0, "missing": []})
            
            for control_id in baseline_controls:
                family = control_id[:2]
                family_analysis[family]["required"] += 1
                if control_id in implemented_set:
                    family_analysis[family]["implemented"] += 1
                else:
                    family_analysis[family]["missing"].append(control_id)
            
            # Calculate compliance percentage
            compliance_percentage = (len(compliant_controls) / len(baseline_controls)) * 100 if baseline_controls else 0
            
            return {
                "target_baseline": target_baseline,
                "compliance_percentage": round(compliance_percentage, 2),
                "total_required": len(baseline_controls),
                "total_implemented": len(implemented_set),
                "compliant_controls": len(compliant_controls),
                "missing_controls": {
                    "count": len(missing_controls),
                    "controls": sorted(list(missing_controls))
                },
                "extra_controls": {
                    "count": len(extra_controls),
                    "controls": sorted(list(extra_controls))
                },
                "family_analysis": dict(family_analysis),
                "recommendations": self._generate_gap_recommendations(family_analysis, missing_controls)
            }
        except Exception as e:
            logger.error(f"Error performing gap analysis: {e}")
            raise

    async def risk_assessment_helper(self, control_ids: List[str]) -> Dict[str, Any]:
        """Help assess risk coverage based on control selection"""
        try:
            controls_data = await self.data_loader.load_controls()
            
            # Analyze control coverage by security objective
            security_objectives = {
                "confidentiality": [],
                "integrity": [],
                "availability": []
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
                "program_management": ["PM"]
            }
            
            coverage_analysis = {}
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
                    "coverage_percentage": round((len(covered_families) / len(families)) * 100, 2) if families else 0
                }
            
            # Overall risk coverage score
            total_categories = len(risk_categories)
            covered_categories = sum(1 for cat in coverage_analysis.values() if cat["control_count"] > 0)
            overall_coverage = round((covered_categories / total_categories) * 100, 2)
            
            return {
                "overall_risk_coverage": overall_coverage,
                "total_controls_analyzed": len(control_ids),
                "risk_category_coverage": coverage_analysis,
                "recommendations": self._generate_risk_recommendations(coverage_analysis),
                "high_priority_gaps": self._identify_critical_gaps(coverage_analysis)
            }
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            raise

    async def compliance_mapping(self, framework: str, control_ids: List[str]) -> Dict[str, Any]:
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
                }
            }
            
            if framework.lower() not in compliance_mappings:
                return {
                    "error": f"Framework '{framework}' not supported",
                    "supported_frameworks": list(compliance_mappings.keys())
                }
            
            framework_map = compliance_mappings[framework.lower()]
            
            # Analyze coverage
            covered_requirements = {}
            uncovered_requirements = {}
            
            for requirement, required_controls in framework_map.items():
                covered_controls = [ctrl for ctrl in required_controls if ctrl in control_ids]
                coverage_percentage = (len(covered_controls) / len(required_controls)) * 100
                
                if coverage_percentage > 0:
                    covered_requirements[requirement] = {
                        "covered_controls": covered_controls,
                        "total_required": len(required_controls),
                        "coverage_percentage": round(coverage_percentage, 2)
                    }
                else:
                    uncovered_requirements[requirement] = {
                        "required_controls": required_controls,
                        "total_required": len(required_controls)
                    }
            
            overall_compliance = round((len(covered_requirements) / len(framework_map)) * 100, 2)
            
            return {
                "framework": framework.upper(),
                "overall_compliance_percentage": overall_compliance,
                "total_requirements": len(framework_map),
                "covered_requirements": len(covered_requirements),
                "uncovered_requirements": len(uncovered_requirements),
                "requirement_details": {
                    "covered": covered_requirements,
                    "uncovered": uncovered_requirements
                },
                "recommendations": self._generate_compliance_recommendations(uncovered_requirements)
            }
        except Exception as e:
            logger.error(f"Error in compliance mapping: {e}")
            raise

    async def control_relationships(self, control_id: str) -> Dict[str, Any]:
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
                    enhancements.append({
                        "id": ctrl_id,
                        "title": ctrl.get("title", ""),
                        "enhancement_number": ctrl_id.split("(")[1].split(")")[0]
                    })
            
            # Find controls that reference this one
            referencing_controls = self._find_referencing_controls(control_id, controls_data)
            
            return {
                "control_id": control_id,
                "control_title": control.get("title", ""),
                "family": control_id[:2],
                "enhancements": {
                    "count": len(enhancements),
                    "details": enhancements
                },
                "related_controls": related_controls,
                "referencing_controls": referencing_controls,
                "implementation_guidance": self._extract_implementation_guidance(control)
            }
        except Exception as e:
            logger.error(f"Error analyzing control relationships: {e}")
            raise

    def _generate_gap_recommendations(self, family_analysis: Dict, missing_controls: Set[str]) -> List[str]:
        """Generate recommendations based on gap analysis"""
        recommendations = []
        
        # Identify families with low coverage
        for family, data in family_analysis.items():
            if data["required"] > 0:
                coverage = (data["implemented"] / data["required"]) * 100
                if coverage < 50:
                    recommendations.append(f"Priority: Implement {family} family controls - only {coverage:.1f}% coverage")
                elif coverage < 80:
                    recommendations.append(f"Improve {family} family controls - {coverage:.1f}% coverage")
        
        # Highlight critical missing controls
        critical_controls = {"AC-1", "AU-1", "CA-1", "CM-1", "CP-1", "IA-1", "IR-1", "PL-1", "RA-1", "SA-1", "SC-1", "SI-1"}
        missing_critical = missing_controls & critical_controls
        
        if missing_critical:
            recommendations.insert(0, f"CRITICAL: Implement foundational controls: {', '.join(sorted(missing_critical))}")
        
        return recommendations

    def _generate_risk_recommendations(self, coverage_analysis: Dict) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        # Identify high-risk gaps
        high_risk_categories = {
            "access_control": "Implement access control measures to prevent unauthorized access",
            "incident_response": "Establish incident response capabilities for security events",
            "system_integrity": "Implement system integrity controls to detect unauthorized changes"
        }
        
        for category, message in high_risk_categories.items():
            if coverage_analysis.get(category, {}).get("control_count", 0) == 0:
                recommendations.append(f"HIGH RISK: {message}")
        
        return recommendations

    def _generate_compliance_recommendations(self, uncovered_requirements: Dict) -> List[str]:
        """Generate compliance-focused recommendations"""
        recommendations = []
        
        if uncovered_requirements:
            recommendations.append("Implement missing controls to achieve full compliance")
            
            # Prioritize by number of required controls
            sorted_reqs = sorted(uncovered_requirements.items(), 
                               key=lambda x: x[1]["total_required"], reverse=True)
            
            for req, data in sorted_reqs[:3]:  # Top 3 gaps
                recommendations.append(f"Priority requirement {req}: {len(data['required_controls'])} controls needed")
        
        return recommendations

    def _find_related_controls(self, control: Dict, controls_data: Dict) -> List[Dict[str, Any]]:
        """Find controls related to the given control"""
        related = []
        control_family = control.get("id", "")[:2]
        
        # Find other controls in the same family
        all_controls = controls_data.get("catalog", {}).get("controls", [])
        for ctrl in all_controls:
            ctrl_id = ctrl.get("id", "")
            if ctrl_id.startswith(control_family) and ctrl_id != control.get("id", ""):
                if not "(" in ctrl_id:  # Exclude enhancements
                    related.append({
                        "id": ctrl_id,
                        "title": ctrl.get("title", ""),
                        "relationship": "same_family"
                    })
        
        return related[:5]  # Limit to 5 related controls

    def _find_referencing_controls(self, control_id: str, controls_data: Dict) -> List[Dict[str, Any]]:
        """Find controls that reference the given control"""
        referencing = []
        all_controls = controls_data.get("catalog", {}).get("controls", [])
        
        for ctrl in all_controls:
            # Check if control text mentions the target control
            ctrl_text = str(ctrl).lower()
            if control_id.lower() in ctrl_text and ctrl.get("id", "") != control_id:
                referencing.append({
                    "id": ctrl.get("id", ""),
                    "title": ctrl.get("title", ""),
                    "relationship": "references"
                })
        
        return referencing[:3]  # Limit to 3 referencing controls

    def _extract_implementation_guidance(self, control: Dict) -> List[str]:
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

    def _identify_critical_gaps(self, coverage_analysis: Dict) -> List[str]:
        """Identify critical security gaps"""
        critical_gaps = []
        
        # Define critical categories
        critical_categories = ["access_control", "incident_response", "system_integrity", "audit_accountability"]
        
        for category in critical_categories:
            if coverage_analysis.get(category, {}).get("control_count", 0) == 0:
                critical_gaps.append(category.replace("_", " ").title())
        
        return critical_gaps