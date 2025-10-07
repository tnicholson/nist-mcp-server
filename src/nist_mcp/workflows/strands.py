"""Strands - Workflow orchestration for automated compliance checks

Provides automated workflow execution for compliance checks per control/family.
Orchestrates complex compliance assessment processes with conditional logic.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
import logging
from enum import Enum

from ..history.storage import HistoricalStorage
from ..monitoring.monitor import ControlMonitor
from ..data.loader import NISTDataLoader

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep:
    """Represents a single step in a compliance workflow"""

    def __init__(
        self,
        step_id: str,
        step_type: str,
        description: str,
        action: Callable,
        parameters: Dict[str, Any] = None,
        depends_on: List[str] = None,
        condition: Callable[[Dict[str, Any]], bool] = None,
        retry_count: int = 0,
        timeout_seconds: int = 300,
    ):
        self.step_id = step_id
        self.step_type = step_type
        self.description = description
        self.action = action
        self.parameters = parameters or {}
        self.depends_on = depends_on or []
        self.condition = condition
        self.retry_count = retry_count
        self.timeout_seconds = timeout_seconds
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.completed_at = None
        self.attempts = 0

    async def execute(self, workflow_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute this workflow step"""
        try:
            # Check condition if provided
            if self.condition and not self.condition(workflow_context):
                self.status = StepStatus.SKIPPED
                logger.info(f"Step {self.step_id} skipped due to condition")
                return {"status": "skipped", "message": "Condition not met"}

            self.status = StepStatus.RUNNING
            self.attempts += 1

            # Execute the action with timeout
            result = await asyncio.wait_for(
                self.action(workflow_context, **self.parameters),
                timeout=self.timeout_seconds,
            )

            self.status = StepStatus.COMPLETED
            self.result = result
            self.completed_at = datetime.now()

            logger.info(f"Step {self.step_id} completed successfully")
            return result

        except asyncio.TimeoutError:
            self.status = StepStatus.FAILED
            self.error = f"Step timed out after {self.timeout_seconds} seconds"
            logger.error(f"Step {self.step_id} timed out")
            return {"status": "error", "error": self.error}

        except Exception as e:
            self.status = StepStatus.FAILED
            self.error = str(e)
            logger.error(f"Step {self.step_id} failed: {e}")
            return {"status": "error", "error": str(e)}


class WorkflowStrand:
    """Represents a complete automated compliance workflow (Strand)"""

    def __init__(
        self,
        strand_id: str,
        name: str,
        description: str,
        target_controls: List[str],
        steps: List[WorkflowStep],
        storage: HistoricalStorage,
        monitor: Optional[ControlMonitor] = None,
        data_loader: Optional[NISTDataLoader] = None,
    ):
        self.strand_id = strand_id
        self.name = name
        self.description = description
        self.target_controls = target_controls
        self.steps = {step.step_id: step for step in steps}
        self.storage = storage
        self.monitor = monitor
        self.data_loader = data_loader
        self.status = WorkflowStatus.PENDING
        self.context = {}
        self.created_at = datetime.now()
        self.completed_at = None
        self.errors = []

    def get_executable_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute (dependencies met)"""
        completed_step_ids = {
            sid
            for sid, step in self.steps.items()
            if step.status == StepStatus.COMPLETED
        }
        executable = []

        for step in self.steps.values():
            if step.status == StepStatus.PENDING:
                # Check if all dependencies are completed
                deps_met = all(dep in completed_step_ids for dep in step.depends_on)
                if deps_met:
                    executable.append(step)

        return executable

    async def execute(self) -> Dict[str, Any]:
        """Execute the complete workflow strand"""
        self.status = WorkflowStatus.RUNNING
        start_time = datetime.now()

        # Record workflow start
        self.storage.record_workflow_run(
            {"workflow_id": self.strand_id, "status": "running"}
        )

        try:
            logger.info(f"Starting workflow strand {self.strand_id}: {self.name}")

            # Initialize context
            self.context = {
                "strand_id": self.strand_id,
                "target_controls": self.target_controls,
                "start_time": start_time.isoformat(),
                "results": {},
                "errors": [],
                "data_loader": self.data_loader,
                "monitor": self.monitor,
            }

            # Execute steps in dependency order
            while True:
                executable_steps = self.get_executable_steps()

                if not executable_steps:
                    # Check if all steps are completed
                    all_completed = all(
                        step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
                        for step in self.steps.values()
                    )
                    if all_completed:
                        break

                    # Check for failures that block progress
                    failed_steps = [
                        step
                        for step in self.steps.values()
                        if step.status == StepStatus.FAILED
                        and step.retry_count >= step.attempts
                    ]
                    if failed_steps:
                        raise Exception(
                            f"Unresolved failures in steps: {[s.step_id for s in failed_steps]}"
                        )

                    # Wait briefly and check again
                    await asyncio.sleep(1)
                    continue

                # Execute steps concurrently if they can run in parallel
                tasks = [step.execute(self.context) for step in executable_steps]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for step, result in zip(executable_steps, results):
                    step_id = step.step_id

                    if isinstance(result, Exception):
                        step.status = StepStatus.FAILED
                        step.error = str(result)
                        self.errors.append(f"Step {step_id}: {result}")
                        self.context["results"][step_id] = {
                            "status": "error",
                            "error": str(result),
                        }
                    else:
                        self.context["results"][step_id] = result

            # Workflow completed successfully
            self.status = WorkflowStatus.COMPLETED
            self.completed_at = datetime.now()

            # Record final results
            self.storage.record_workflow_run(
                {
                    "workflow_id": self.strand_id,
                    "status": "completed",
                    "results": self._generate_final_results(),
                }
            )

            logger.info(f"Workflow strand {self.strand_id} completed successfully")
            return self._generate_final_results()

        except Exception as e:
            self.status = WorkflowStatus.FAILED
            self.completed_at = datetime.now()
            error_msg = f"Workflow failed: {str(e)}"

            self.storage.record_workflow_run(
                {
                    "workflow_id": self.strand_id,
                    "status": "failed",
                    "error_message": error_msg,
                }
            )

            logger.error(f"Workflow strand {self.strand_id} failed: {e}")
            raise

    def _generate_final_results(self) -> Dict[str, Any]:
        """Generate final workflow results"""
        step_results = {}
        for step_id, step in self.steps.items():
            step_results[step_id] = {
                "status": step.status.value,
                "result": step.result,
                "error": step.error,
                "attempts": step.attempts,
                "completed_at": step.completed_at.isoformat()
                if step.completed_at
                else None,
            }

        return {
            "strand_id": self.strand_id,
            "name": self.name,
            "status": self.status.value,
            "target_controls": self.target_controls,
            "step_results": step_results,
            "context": self.context,
            "errors": self.errors,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_seconds": (self.completed_at - self.created_at).total_seconds()
            if self.completed_at
            else None,
        }


class StrandsOrchestrator:
    """Main orchestrator for compliance workflow strands"""

    def __init__(
        self,
        storage: HistoricalStorage,
        monitor: Optional[ControlMonitor] = None,
        data_loader: Optional[NISTDataLoader] = None,
    ):
        self.storage = storage
        self.monitor = monitor
        self.data_loader = data_loader
        self.active_strands: Dict[str, WorkflowStrand] = {}
        self.strand_definitions: Dict[str, Dict[str, Any]] = {}

    def register_strand_definition(
        self,
        strand_type: str,
        name: str,
        description: str,
        step_builder: Callable[[List[str]], List[WorkflowStep]],
    ) -> None:
        """Register a reusable strand definition"""
        self.strand_definitions[strand_type] = {
            "name": name,
            "description": description,
            "step_builder": step_builder,
        }

        logger.info(f"Registered strand definition: {strand_type}")

    def create_strand(
        self, strand_type: str, target_controls: List[str], **kwargs
    ) -> WorkflowStrand:
        """Create a new workflow strand"""
        if strand_type not in self.strand_definitions:
            raise ValueError(f"Unknown strand type: {strand_type}")

        definition = self.strand_definitions[strand_type]
        strand_id = f"strand_{strand_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Build steps for this strand
        steps = definition["step_builder"](target_controls, **kwargs)

        strand = WorkflowStrand(
            strand_id=strand_id,
            name=definition["name"],
            description=definition["description"],
            target_controls=target_controls,
            steps=steps,
            storage=self.storage,
            monitor=self.monitor,
            data_loader=self.data_loader,
        )

        self.active_strands[strand_id] = strand
        return strand

    async def execute_strand_async(self, strand: WorkflowStrand) -> Dict[str, Any]:
        """Execute a strand asynchronously"""
        try:
            return await strand.execute()
        finally:
            # Clean up completed strands
            if strand.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
                if strand.strand_id in self.active_strands:
                    del self.active_strands[strand.strand_id]

    def get_strand_status(self, strand_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific strand"""
        if strand_id in self.active_strands:
            strand = self.active_strands[strand_id]
            return {
                "strand_id": strand_id,
                "name": strand.name,
                "status": strand.status.value,
                "progress": len(
                    [
                        s
                        for s in strand.steps.values()
                        if s.status == StepStatus.COMPLETED
                    ]
                )
                / len(strand.steps),
                "target_controls": strand.target_controls,
                "errors": strand.errors,
            }
        return None

    def get_active_strands(self) -> List[Dict[str, Any]]:
        """Get all active strands"""
        return [
            self.get_strand_status(strand_id)
            for strand_id in self.active_strands.keys()
        ]


# Predefined strand types and their step builders


async def gap_analysis_step(
    context: Dict[str, Any], baseline: str = "moderate"
) -> Dict[str, Any]:
    """Step to perform gap analysis"""
    data_loader = context.get("data_loader")
    if not data_loader:
        raise ValueError("Data loader not provided in workflow context")

    from ..analysis_tools import NISTAnalysisTools

    analysis = NISTAnalysisTools(data_loader)
    target_controls = context.get("target_controls", [])

    # Simulate implemented controls (in practice, this would come from evidence)
    implemented_controls = [
        ctrl for ctrl in target_controls if hash(ctrl) % 3 != 0
    ]  # Random simulation

    result = await analysis.gap_analysis(implemented_controls, baseline)

    # Update context with results
    context["gap_analysis_result"] = result

    return {"step_type": "gap_analysis", "baseline": baseline, "result": result}


async def monitoring_check_step(
    context: Dict[str, Any], controls_to_check: List[str] = None
) -> Dict[str, Any]:
    """Step to perform monitoring checks on controls"""
    monitor = context.get("monitor")  # Would be injected
    controls = controls_to_check or context.get("target_controls", [])

    check_results = {}
    for control_id in controls:
        if monitor:
            # Use monitor for real checks
            result = await monitor.run_immediate_check(control_id)
        else:
            # Simulate result
            result = {
                "status": "pass" if hash(control_id) % 4 != 0 else "fail",
                "control_id": control_id,
                "timestamp": datetime.now().isoformat(),
            }
        check_results[control_id] = result

    context["monitoring_results"] = check_results

    return {
        "step_type": "monitoring_check",
        "controls_checked": controls,
        "results": check_results,
    }


async def evidence_collection_step(context: Dict[str, Any]) -> Dict[str, Any]:
    """Step to collect evidence for controls"""
    target_controls = context.get("target_controls", [])

    # Simulate evidence collection
    evidence_results = {}
    for control_id in target_controls:
        evidence_results[control_id] = {
            "evidence_found": hash(control_id + "evidence") % 2 == 0,
            "evidence_count": hash(control_id) % 5 + 1,
            "timestamp": datetime.now().isoformat(),
        }

    context["evidence_results"] = evidence_results

    return {"step_type": "evidence_collection", "results": evidence_results}


async def remediation_planning_step(context: Dict[str, Any]) -> Dict[str, Any]:
    """Step to create remediation plans based on results"""
    gap_results = context.get("gap_analysis_result", {})
    monitoring_results = context.get("monitoring_results", {})

    # Generate remediation actions based on gaps and failures
    remediation_actions = []

    missing_controls = gap_results.get("missing_controls", {}).get("controls", [])
    for control_id in missing_controls:
        remediation_actions.append(
            {
                "control_id": control_id,
                "action_type": "implement",
                "priority": "high",
                "description": f"Implement missing control {control_id}",
            }
        )

    # Check monitoring failures
    for control_id, check_result in monitoring_results.items():
        if check_result.get("status") == "fail":
            remediation_actions.append(
                {
                    "control_id": control_id,
                    "action_type": "remediate",
                    "priority": "critical",
                    "description": f"Address monitoring failure for {control_id}",
                }
            )

    context["remediation_plan"] = remediation_actions

    return {
        "step_type": "remediation_planning",
        "actions_created": len(remediation_actions),
        "actions": remediation_actions,
    }


def create_compliance_assessment_strand(
    target_controls: List[str], **kwargs
) -> List[WorkflowStep]:
    """Create steps for a compliance assessment strand"""
    return [
        WorkflowStep(
            step_id="evidence_collection",
            step_type="evidence",
            description="Collect evidence for target controls",
            action=evidence_collection_step,
            parameters={},
        ),
        WorkflowStep(
            step_id="gap_analysis",
            step_type="analysis",
            description="Perform gap analysis against baseline",
            action=gap_analysis_step,
            parameters={"baseline": kwargs.get("baseline", "moderate")},
            depends_on=["evidence_collection"],
        ),
        WorkflowStep(
            step_id="monitoring_check",
            step_type="monitoring",
            description="Run monitoring checks on controls",
            action=monitoring_check_step,
            parameters={"controls_to_check": target_controls},
            depends_on=["gap_analysis"],
        ),
        WorkflowStep(
            step_id="remediation_planning",
            step_type="planning",
            description="Create remediation plans for gaps",
            action=remediation_planning_step,
            parameters={},
            depends_on=["gap_analysis", "monitoring_check"],
        ),
    ]


def create_family_assessment_strand(
    target_controls: List[str], **kwargs
) -> List[WorkflowStep]:
    """Create steps for a family-specific assessment strand"""
    family = kwargs.get("family", "AC")

    # Filter controls by family
    family_controls = [
        ctrl for ctrl in target_controls if ctrl.startswith(f"{family}-")
    ]

    return [
        WorkflowStep(
            step_id="family_evidence_collection",
            step_type="evidence",
            description=f"Collect evidence for {family} family controls",
            action=evidence_collection_step,
            parameters={},
        ),
        WorkflowStep(
            step_id="family_monitoring",
            step_type="monitoring",
            description=f"Monitor {family} family controls",
            action=monitoring_check_step,
            parameters={"controls_to_check": family_controls},
            depends_on=["family_evidence_collection"],
        ),
        WorkflowStep(
            step_id="family_gap_analysis",
            step_type="analysis",
            description=f"Analyze gaps in {family} family",
            action=gap_analysis_step,
            parameters={"baseline": kwargs.get("baseline", "moderate")},
            depends_on=["family_monitoring"],
        ),
    ]
