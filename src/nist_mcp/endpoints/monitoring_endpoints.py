"""Monitoring and workflow MCP tool endpoints"""

import logging
from datetime import datetime
from typing import Any, Optional

from mcp.server import FastMCP

from ..history.storage import HistoricalStorage
from ..monitoring.monitor import ControlMonitor
from ..workflows.strands import StrandsOrchestrator, create_compliance_assessment_strand
from ..connectors.base import connector_registry
from ..connectors.aws import AWSConnector

logger = logging.getLogger(__name__)

# Initialize components globally (refactor later to dependency injection)
_storage = HistoricalStorage()
_monitor = ControlMonitor(_storage)
_orchestrator = StrandsOrchestrator(_storage, _monitor)

# Register connector types
connector_registry.register_connector_type("aws", AWSConnector)


async def _ensure_initialized():
    """Ensure components are initialized"""
    await _storage.initialize()
    await _orchestrator.orchestrator.storage.initialize()  # type: ignore


def register_monitoring_endpoints(app: FastMCP, loader: Any) -> None:
    """Register all monitoring and workflow endpoints with the MCP app"""

    @app.tool()
    async def validate_oscal_document(
        document: dict[str, Any], document_type: str = "catalog"
    ) -> dict[str, Any]:
        """Validate an OSCAL document against its JSON schema"""
        try:
            import jsonschema

            schemas_data = await loader.load_oscal_schemas()
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

    @app.tool()
    async def start_continuous_monitoring(
        control_id: str, check_interval_hours: int = 24, connector_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Start continuous monitoring for a specific control"""
        await _ensure_initialized()

        monitor_id = _monitor.start_monitoring_control(
            control_id=control_id,
            check_interval_hours=check_interval_hours,
            connector_id=connector_id,
            check_type="continuous",
        )

        return {
            "monitor_id": monitor_id,
            "control_id": control_id,
            "interval_hours": check_interval_hours,
            "status": "started",
            "message": f"Continuous monitoring started for control {control_id}",
        }

    @app.tool()
    async def stop_continuous_monitoring(monitor_id: str) -> dict[str, Any]:
        """Stop continuous monitoring for a control"""
        success = _monitor.stop_monitoring(monitor_id)

        if success:
            return {
                "monitor_id": monitor_id,
                "status": "stopped",
                "message": "Continuous monitoring stopped successfully",
            }
        else:
            return {
                "monitor_id": monitor_id,
                "status": "error",
                "message": "Monitor not found or already stopped",
            }

    @app.tool()
    async def get_monitoring_status() -> dict[str, Any]:
        """Get status of all monitoring activities"""
        return _monitor.get_monitoring_status()

    @app.tool()
    async def run_manual_check(
        control_id: str, connector_id: Optional[str] = None
    ) -> dict[str, Any]:
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
        _storage.record_monitoring_check(
            {
                "control_id": control_id,
                "check_type": "manual",
                "connector_id": connector_id,
                "status": result.get("status", "unknown"),
                "result_details": result,
                "evidence_paths": result.get("evidence_paths", []),
            }
        )

        return result

    @app.tool()
    async def execute_compliance_workflow(
        target_controls: list[str],
        workflow_type: str = "compliance_assessment",
        baseline: str = "moderate",
    ) -> dict[str, Any]:
        """Execute an automated compliance workflow (Strand)"""
        await _ensure_initialized()

        # Register strand definitions
        _orchestrator.register_strand_definition(
            "compliance_assessment",
            "Compliance Assessment Workflow",
            "Automated compliance assessment with gap analysis and remediation planning",
            create_compliance_assessment_strand,
        )

        # Create and execute strand
        strand = _orchestrator.create_strand(
            workflow_type, target_controls, baseline=baseline
        )

        result = await _orchestrator.execute_strand_async(strand)

        return result

    @app.tool()
    async def get_workflow_history(
        workflow_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
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
            "timestamp": datetime.now().isoformat(),
        }

    @app.tool()
    async def create_remediation_action(
        control_id: str,
        action_type: str,
        description: str,
        priority: str = "medium",
        assessment_id: Optional[str] = None,
        assigned_to: Optional[str] = None,
        due_date: Optional[str] = None,
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
                "Verify effectiveness",
            ]
            evidence_required = [
                f"Screenshots of {control_id} configuration",
                f"Test results for {control_id} implementation",
                "Documentation of implementation steps",
            ]
        elif action_type == "enhance":
            implementation_steps = [
                f"Assess current {control_id} implementation",
                "Identify enhancement opportunities",
                f"Implement {control_id} enhancements",
                "Test enhanced controls",
                "Update documentation",
            ]
            evidence_required = [
                f"Assessment report for current {control_id} implementation",
                f"Enhancement test results for {control_id}",
            ]
        elif action_type == "document":
            implementation_steps = [
                f"Review current {control_id} documentation",
                f"Update {control_id} procedures",
                "Validate documentation accuracy",
                "Train relevant personnel",
            ]
            evidence_required = [f"Updated {control_id} documentation", "Training records"]

        action_id = _storage.create_remediation_action(
            {
                "control_id": control_id,
                "assessment_id": assessment_id,
                "action_type": action_type,
                "description": description,
                "priority": priority,
                "status": "pending",
                "assigned_to": assigned_to,
                "due_date": due_date,
                "implementation_steps": implementation_steps,
                "evidence_required": evidence_required,
            }
        )

        return {
            "action_id": action_id,
            "control_id": control_id,
            "status": "created",
            "message": f"Remediation action created for {control_id}",
        }

    @app.tool()
    async def get_remediation_actions(
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        control_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get remediation actions with optional filtering"""
        await _ensure_initialized()

        return _storage.get_remediation_actions(
            status_filter=status_filter,
            priority_filter=priority_filter,
            control_id=control_id,
            limit=limit,
        )

    @app.tool()
    async def get_overdue_remediations() -> list[dict[str, Any]]:
        """Get all overdue remediation actions"""
        await _ensure_initialized()

        return _storage.get_overdue_remediation_actions()

    @app.tool()
    async def update_remediation_status(
        action_id: str, status: str, outcome: Optional[dict[str, Any]] = None
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
                "outcome": outcome,
            }
        else:
            return {
                "action_id": action_id,
                "status": "error",
                "updated": False,
                "message": "Action not found or update failed",
            }

    @app.tool()
    async def register_connector(
        connector_type: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Register a new connector for external system integration"""
        connector = connector_registry.create_connector(connector_type, config)

        if connector:
            # Save connector in storage
            connector_id = _storage.register_connector(
                {
                    "name": config.get("name", connector.connector_id),
                    "type": connector_type,
                    "config": config,
                    "status": "active",
                }
            )

            # Register with monitor system
            _monitor.register_connector(connector.connector_id, connector)

            return {
                "connector_id": connector_id,
                "type": connector_type,
                "status": "registered",
                "message": f"Connector '{connector.name}' registered successfully",
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to register connector of type '{connector_type}'",
            }

    @app.tool()
    async def list_connectors() -> list[dict[str, Any]]:
        """List all registered connectors"""
        return connector_registry.list_connectors()

    @app.tool()
    async def get_monitoring_history(
        control_id: Optional[str] = None, days: int = 7
    ) -> list[dict[str, Any]]:
        """Get monitoring check history"""
        await _ensure_initialized()

        return (
            _monitor.get_all_monitoring_history(days)
            if control_id is None
            else _monitor.get_control_monitoring_history(control_id, days)
        )

    @app.tool()
    async def gap_analysis_with_history(
        implemented_controls: list[str],
        target_baseline: str = "moderate",
        create_remediations: bool = True,
    ) -> dict[str, Any]:
        """Perform gap analysis and save results to history with optional remediation planning"""
        # Perform the analysis
        from ..analysis_tools import NISTAnalysisTools

        analysis = NISTAnalysisTools(loader)
        result = await analysis.gap_analysis(implemented_controls, target_baseline)

        # Save to history
        await _ensure_initialized()
        assessment_id = _storage.save_assessment(
            {
                "assessment_type": "gap_analysis_with_history",
                "target_baseline": target_baseline,
                "input_controls": implemented_controls,
                "implemented_controls": implemented_controls,
                "results": result,
                "compliance_score": result.get("compliance_percentage"),
                "created_by": "gap_analysis_with_history_tool",
            }
        )

        # Create remediation actions for missing controls if requested
        if create_remediations:
            missing_controls = result.get("missing_controls", {}).get("controls", [])
            remediation_actions = []

            for control_id in missing_controls:
                action_id = _storage.create_remediation_action(
                    {
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
                            f"Document {control_id} implementation and evidence",
                        ],
                        "evidence_required": [
                            f"Screenshots of {control_id} configuration",
                            f"Test results demonstrating {control_id} effectiveness",
                            f"Documentation of {control_id} implementation",
                        ],
                    }
                )
                remediation_actions.append(
                    {
                        "control_id": control_id,
                        "action_id": action_id,
                        "action_type": "implement",
                    }
                )

            result["remediation_actions_created"] = len(remediation_actions)
            result["remediation_details"] = remediation_actions

        result["assessment_id"] = assessment_id
        result["saved_to_history"] = True

        return result
