"""Historical tracking and database storage for NIST MCP Server

Provides persistent storage for assessments, monitoring results, and remediation tracking.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class HistoricalStorage:
    """SQLite-based historical data storage"""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "history.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Initialize database schema"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assessments (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,  -- 'gap_analysis', 'cmmc_readiness', 'fedramp_assessment', etc.
                    target_baseline TEXT,
                    target_level INTEGER,
                    input_controls TEXT,  -- JSON array of control IDs
                    implemented_controls TEXT,  -- JSON array of implemented control IDs
                    results TEXT,  -- JSON results
                    compliance_score REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_checks (
                    id TEXT PRIMARY KEY,
                    assessment_id TEXT,
                    control_id TEXT NOT NULL,
                    check_type TEXT NOT NULL,  -- 'automated', 'manual', 'connector'
                    connector_id TEXT,
                    status TEXT NOT NULL,  -- 'pass', 'fail', 'warning', 'unknown'
                    result_details TEXT,  -- JSON result details
                    evidence_paths TEXT,  -- JSON array of evidence paths
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    next_check_scheduled DATETIME,
                    FOREIGN KEY (assessment_id) REFERENCES assessments(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS remediation_actions (
                    id TEXT PRIMARY KEY,
                    control_id TEXT NOT NULL,
                    assessment_id TEXT,
                    action_type TEXT NOT NULL,  -- 'implement', 'enhance', 'monitor', 'document'
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,  -- 'critical', 'high', 'medium', 'low'
                    status TEXT NOT NULL,  -- 'pending', 'in_progress', 'completed', 'cancelled'
                    assigned_to TEXT,
                    due_date DATE,
                    implementation_steps TEXT,  -- JSON array of steps
                    evidence_required TEXT,  -- JSON array of required evidence
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    outcome TEXT,  -- JSON outcome details
                    FOREIGN KEY (assessment_id) REFERENCES assessments(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS connectors (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,  -- 'api', 'file', 'database', 'cloud_service'
                    config TEXT,  -- JSON configuration
                    status TEXT NOT NULL,  -- 'active', 'inactive', 'error'
                    last_used DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    type TEXT NOT NULL,  -- 'compliance_check', 'vulnerability_scan', 'evidence_collection'
                    target_controls TEXT,  -- JSON array of target control IDs
                    schedule_config TEXT,  -- JSON schedule configuration
                    connector_ids TEXT,  -- JSON array of connector IDs to use
                    status TEXT NOT NULL,  -- 'active', 'inactive', 'running'
                    last_run DATETIME,
                    next_run DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT NOT NULL,  -- 'running', 'completed', 'failed', 'cancelled'
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    results TEXT,  -- JSON run results
                    error_message TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
            """)

            # Create indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_type ON assessments(type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_timestamp ON assessments(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_monitoring_assessment ON monitoring_checks(assessment_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_monitoring_control ON monitoring_checks(control_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_remediation_control ON remediation_actions(control_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_remediation_status ON remediation_actions(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)"
            )

            logger.info("Historical storage initialized")

    def _connect(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_assessment(self, assessment_data: Dict[str, Any]) -> str:
        """Save assessment results to history"""
        assessment_id = f"assess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assessments (
                    id, type, target_baseline, target_level, input_controls,
                    implemented_controls, results, compliance_score, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    assessment_id,
                    assessment_data.get("assessment_type", "gap_analysis"),
                    assessment_data.get("target_baseline"),
                    assessment_data.get("target_level"),
                    json.dumps(assessment_data.get("input_controls", [])),
                    json.dumps(assessment_data.get("implemented_controls", [])),
                    json.dumps(assessment_data.get("results", {})),
                    assessment_data.get("compliance_score"),
                    assessment_data.get("created_by", "system"),
                ),
            )

        logger.info(f"Saved assessment {assessment_id}")
        return assessment_id

    def get_assessments(
        self, assessment_type: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get historical assessments"""
        with self._connect() as conn:
            query = "SELECT * FROM assessments WHERE 1=1"
            params = []

            if assessment_type:
                query += " AND type = ?"
                params.append(assessment_type)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

            return [dict(row) for row in rows]

    def get_assessment_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get assessment trends over time"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with self._connect() as conn:
            # Get compliance score trends
            rows = conn.execute(
                """
                SELECT
                    DATE(timestamp) as date,
                    AVG(compliance_score) as avg_score,
                    COUNT(*) as assessment_count
                FROM assessments
                WHERE timestamp >= ? AND compliance_score IS NOT NULL
                GROUP BY DATE(timestamp)
                ORDER BY date
            """,
                (cutoff_date.isoformat(),),
            ).fetchall()

            scores_over_time = []
            for row in rows:
                scores_over_time.append(
                    {
                        "date": row["date"],
                        "average_score": round(row["avg_score"], 2),
                        "assessment_count": row["assessment_count"],
                    }
                )

            # Get assessment type distribution
            type_rows = conn.execute(
                """
                SELECT type, COUNT(*) as count
                FROM assessments
                WHERE timestamp >= ?
                GROUP BY type
                ORDER BY count DESC
            """,
                (cutoff_date.isoformat(),),
            ).fetchall()

            type_distribution = [
                {"type": row["type"], "count": row["count"]} for row in type_rows
            ]

            return {
                "period_days": days,
                "scores_over_time": scores_over_time,
                "assessment_type_distribution": type_distribution,
                "total_assessments": sum(t["count"] for t in type_distribution),
            }

    def record_monitoring_check(self, check_data: Dict[str, Any]) -> str:
        """Record a monitoring check result"""
        check_id = f"check_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO monitoring_checks (
                    id, assessment_id, control_id, check_type, connector_id,
                    status, result_details, evidence_paths, next_check_scheduled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    check_id,
                    check_data.get("assessment_id"),
                    check_data["control_id"],
                    check_data["check_type"],
                    check_data.get("connector_id"),
                    check_data["status"],
                    json.dumps(check_data.get("result_details", {})),
                    json.dumps(check_data.get("evidence_paths", [])),
                    check_data.get("next_check_scheduled"),
                ),
            )

        return check_id

    def get_monitoring_history(
        self,
        control_id: Optional[str] = None,
        days: int = 7,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get monitoring check history"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with self._connect() as conn:
            query = "SELECT * FROM monitoring_checks WHERE timestamp >= ?"
            params = [cutoff_date.isoformat()]

            if control_id:
                query += " AND control_id = ?"
                params.append(control_id)

            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)

            query += " ORDER BY timestamp DESC"

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_monitoring_status(self, control_ids: List[str]) -> Dict[str, Any]:
        """Get current monitoring status for controls"""
        placeholders = ",".join("?" * len(control_ids))

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    control_id,
                    status,
                    timestamp,
                    ROW_NUMBER() OVER (PARTITION BY control_id ORDER BY timestamp DESC) as rn
                FROM monitoring_checks
                WHERE control_id IN ({placeholders}) AND timestamp >= ?
            """,
                control_ids + [(datetime.now() - timedelta(days=30)).isoformat()],
            ).fetchall()

            status_summary = {}
            for row in rows:
                if row["rn"] == 1:  # Most recent check per control
                    status_summary[row["control_id"]] = {
                        "latest_status": row["status"],
                        "last_checked": row["timestamp"],
                        "days_since_check": (
                            datetime.now() - datetime.fromisoformat(row["timestamp"])
                        ).days,
                    }

            # Fill in controls with no checks
            for control_id in control_ids:
                if control_id not in status_summary:
                    status_summary[control_id] = {
                        "latest_status": "never_checked",
                        "last_checked": None,
                        "days_since_check": None,
                    }

            return status_summary

    def create_remediation_action(self, action_data: Dict[str, Any]) -> str:
        """Create a new remediation action"""
        action_id = f"remed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        due_date = action_data.get("due_date")
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date).date()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO remediation_actions (
                    id, control_id, assessment_id, action_type, description,
                    priority, status, assigned_to, due_date, implementation_steps,
                    evidence_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    action_id,
                    action_data["control_id"],
                    action_data.get("assessment_id"),
                    action_data["action_type"],
                    action_data["description"],
                    action_data["priority"],
                    action_data.get("status", "pending"),
                    action_data.get("assigned_to"),
                    due_date,
                    json.dumps(action_data.get("implementation_steps", [])),
                    json.dumps(action_data.get("evidence_required", [])),
                ),
            )

        logger.info(f"Created remediation action {action_id}")
        return action_id

    def update_remediation_status(
        self, action_id: str, status: str, outcome: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update remediation action status"""
        completed_at = datetime.now() if status == "completed" else None

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE remediation_actions
                SET status = ?, updated_at = ?, completed_at = ?, outcome = ?
                WHERE id = ?
            """,
                (
                    status,
                    datetime.now(),
                    completed_at,
                    json.dumps(outcome) if outcome else None,
                    action_id,
                ),
            )

            return conn.total_changes > 0

    def get_remediation_actions(
        self,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        control_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get remediation actions with optional filters"""
        with self._connect() as conn:
            query = "SELECT * FROM remediation_actions WHERE 1=1"
            params = []

            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)

            if priority_filter:
                query += " AND priority = ?"
                params.append(priority_filter)

            if control_id:
                query += " AND control_id = ?"
                params.append(control_id)

            query += " ORDER BY " + (
                "due_date, priority DESC"
                if priority_filter == "urgent"
                else "priority DESC, due_date"
            )

            query += " LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_overdue_remediation_actions(self) -> List[Dict[str, Any]]:
        """Get overdue remediation actions"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM remediation_actions
                WHERE status IN ('pending', 'in_progress')
                AND due_date < ?
                ORDER BY due_date asc, priority desc
            """,
                (datetime.now().date().isoformat(),),
            ).fetchall()

            return [dict(row) for row in rows]

    def register_connector(self, connector_data: Dict[str, Any]) -> str:
        """Register a new connector"""
        connector_id = f"conn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO connectors (id, name, type, config, status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    connector_id,
                    connector_data["name"],
                    connector_data["type"],
                    json.dumps(connector_data.get("config", {})),
                    connector_data.get("status", "active"),
                ),
            )

        return connector_id

    def update_connector_status(self, connector_id: str, status: str) -> bool:
        """Update connector status"""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE connectors
                SET status = ?, last_used = ?
                WHERE id = ?
            """,
                (status, datetime.now(), connector_id),
            )

            return conn.total_changes > 0

    def create_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Create a new workflow"""
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflows (
                    id, name, description, type, target_controls, schedule_config,
                    connector_ids, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    workflow_id,
                    workflow_data["name"],
                    workflow_data.get("description"),
                    workflow_data["type"],
                    json.dumps(workflow_data.get("target_controls", [])),
                    json.dumps(workflow_data.get("schedule_config", {})),
                    json.dumps(workflow_data.get("connector_ids", [])),
                    workflow_data.get("status", "active"),
                ),
            )

        logger.info(f"Created workflow {workflow_id}")
        return workflow_id

    def record_workflow_run(self, run_data: Dict[str, Any]) -> str:
        """Record a workflow run"""
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_runs (
                    id, workflow_id, status, results, error_message
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    run_id,
                    run_data["workflow_id"],
                    run_data["status"],
                    json.dumps(run_data.get("results", {})),
                    run_data.get("error_message"),
                ),
            )

            # Update workflow last_run
            conn.execute(
                """
                UPDATE workflows
                SET last_run = ?, updated_at = ?
                WHERE id = ?
            """,
                (datetime.now(), datetime.now(), run_data["workflow_id"]),
            )

        return run_id

    def get_workflow_runs(
        self, workflow_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get workflow run history"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT wr.*, w.name as workflow_name
                FROM workflow_runs wr
                JOIN workflows w ON wr.workflow_id = w.id
                WHERE wr.workflow_id = ?
                ORDER BY wr.started_at DESC
                LIMIT ?
            """,
                (workflow_id, limit),
            ).fetchall()

            return [dict(row) for row in rows]

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT * FROM workflows
                WHERE status = 'active'
                ORDER BY created_at
            """).fetchall()

            return [dict(row) for row in rows]

    def cleanup_old_data(self, days_to_keep: int = 365) -> Dict[str, int]:
        """Clean up old historical data"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with self._connect() as conn:
            # Remove old assessments and related data
            count_assessment = conn.execute(
                "DELETE FROM assessments WHERE timestamp < ?",
                (cutoff_date.isoformat(),),
            ).rowcount

            count_monitoring = conn.execute(
                "DELETE FROM monitoring_checks WHERE timestamp < ?",
                (cutoff_date.isoformat(),),
            ).rowcount

            count_workflow_runs = conn.execute(
                "DELETE FROM workflow_runs WHERE started_at < ?",
                (cutoff_date.isoformat(),),
            ).rowcount

            return {
                "assessments_removed": count_assessment,
                "monitoring_checks_removed": count_monitoring,
                "workflow_runs_removed": count_workflow_runs,
            }
