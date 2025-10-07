"""Evidence collection and management for NIST MCP Server

Provides data structures and validation for cybersecurity evidence
collected against NIST controls.
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import aiofiles
except ImportError:
    aiofiles = None

logger = logging.getLogger(__name__)


class EvidenceType(Enum):
    """Types of evidence that can be collected"""

    POLICY = "policy"
    PROCEDURE = "procedure"
    SCREENSHOT = "screenshot"
    LOG = "log"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    INTERVIEW = "interview"
    TEST_RESULT = "test_result"
    TOOL_OUTPUT = "tool_output"
    OTHER = "other"


class EvidenceStatus(Enum):
    """Status of evidence collection and evaluation"""

    PENDING = "pending"
    COLLECTED = "collected"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class EvidenceItem:
    """Represents a single piece of evidence for a control"""

    def __init__(
        self,
        control_id: str,
        evidence_type: EvidenceType,
        content: str | dict[str, Any],
        description: str = "",
        source: str = "",
        collected_by: str = "",
        collected_date: datetime | None = None,
        reviewer: str = "",
        review_date: datetime | None = None,
        status: EvidenceStatus = EvidenceStatus.COLLECTED,
        metadata: dict[str, Any] | None = None
    ):
        self.id = str(uuid4())
        self.control_id = control_id.upper()
        self.evidence_type = evidence_type
        self.content = content
        self.description = description
        self.source = source
        self.collected_by = collected_by
        self.collected_date = collected_date or datetime.now(timezone.utc)
        self.reviewer = reviewer
        self.review_date = review_date
        self.status = status
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert evidence item to dictionary"""
        return {
            "id": self.id,
            "control_id": self.control_id,
            "evidence_type": self.evidence_type.value,
            "content": self.content,
            "description": self.description,
            "source": self.source,
            "collected_by": self.collected_by,
            "collected_date": self.collected_date.isoformat(),
            "reviewer": self.reviewer,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "status": self.status.value,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'EvidenceItem':
        """Create evidence item from dictionary"""
        return cls(
            control_id=data["control_id"],
            evidence_type=EvidenceType(data["evidence_type"]),
            content=data["content"],
            description=data.get("description", ""),
            source=data.get("source", ""),
            collected_by=data.get("collected_by", ""),
            collected_date=datetime.fromisoformat(data["collected_date"]) if data.get("collected_date") else None,
            reviewer=data.get("reviewer", ""),
            review_date=datetime.fromisoformat(data["review_date"]) if data.get("review_date") else None,
            status=EvidenceStatus(data.get("status", "collected")),
            metadata=data.get("metadata", {})
        )


class EvidenceCollection:
    """Manages a collection of evidence for multiple controls"""

    def __init__(self, name: str = "default", description: str = ""):
        self.id = str(uuid4())
        self.name = name
        self.description = description
        self.created_date = datetime.now(timezone.utc)
        self.evidence_items: dict[str, list[EvidenceItem]] = {}  # control_id -> list of evidence

    def add_evidence(self, evidence_item: EvidenceItem) -> None:
        """Add evidence item to collection"""
        if evidence_item.control_id not in self.evidence_items:
            self.evidence_items[evidence_item.control_id] = []

        self.evidence_items[evidence_item.control_id].append(evidence_item)
        logger.info(f"Added evidence {evidence_item.id} for control {evidence_item.control_id}")

    def get_evidence_for_control(self, control_id: str) -> list[EvidenceItem]:
        """Get all evidence for a specific control"""
        return self.evidence_items.get(control_id.upper(), [])

    def get_all_controls(self) -> list[str]:
        """Get list of all controls with evidence"""
        return list(self.evidence_items.keys())

    def get_summary(self) -> dict[str, Any]:
        """Get summary of evidence collection"""
        total_evidence = sum(len(items) for items in self.evidence_items.values())
        status_counts = {}

        for control_evidence in self.evidence_items.values():
            for evidence in control_evidence:
                status = evidence.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "collection_id": self.id,
            "name": self.name,
            "description": self.description,
            "created_date": self.created_date.isoformat(),
            "total_controls": len(self.evidence_items),
            "total_evidence_items": total_evidence,
            "status_breakdown": status_counts
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert collection to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_date": self.created_date.isoformat(),
            "evidence_items": {
                control_id: [item.to_dict() for item in items]
                for control_id, items in self.evidence_items.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'EvidenceCollection':
        """Create collection from dictionary"""
        collection = cls(
            name=data.get("name", "default"),
            description=data.get("description", "")
        )
        collection.id = data["id"]
        collection.created_date = datetime.fromisoformat(data["created_date"])

        for control_id, items_data in data.get("evidence_items", {}).items():
            collection.evidence_items[control_id] = [
                EvidenceItem.from_dict(item_data) for item_data in items_data
            ]

        return collection


class EvidenceManager:
    """Manages evidence collections and persistence"""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path("data/evidence")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.collections: dict[str, EvidenceCollection] = {}
        self.active_collection: str | None = None

    async def initialize(self) -> None:
        """Initialize evidence manager and load existing collections"""
        # Load all collection files
        for collection_file in self.storage_path.glob("*.json"):
            try:
                async with aiofiles.open(collection_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    collection = EvidenceCollection.from_dict(data)
                    self.collections[collection.id] = collection
                    logger.info(f"Loaded evidence collection: {collection.name}")
            except Exception as e:
                logger.error(f"Failed to load collection {collection_file}: {e}")

        # Set default active collection if none exists
        if not self.active_collection and self.collections:
            self.active_collection = list(self.collections.keys())[0]

    def create_collection(self, name: str, description: str = "") -> str:
        """Create a new evidence collection"""
        collection = EvidenceCollection(name=name, description=description)
        self.collections[collection.id] = collection
        self.active_collection = collection.id

        # Save immediately
        self._save_collection(collection)
        logger.info(f"Created evidence collection: {name}")

        return collection.id

    def set_active_collection(self, collection_id: str) -> bool:
        """Set the active evidence collection"""
        if collection_id in self.collections:
            self.active_collection = collection_id
            return True
        return False

    def get_active_collection(self) -> EvidenceCollection | None:
        """Get the currently active evidence collection"""
        if self.active_collection:
            return self.collections.get(self.active_collection)
        return None

    def add_evidence(self,
                    control_id: str,
                    evidence_type: EvidenceType,
                    content: str | dict[str, Any],
                    description: str = "",
                    source: str = "",
                    collected_by: str = "") -> str | None:
        """Add evidence to the active collection"""
        collection = self.get_active_collection()
        if not collection:
            logger.warning("No active evidence collection")
            return None

        evidence_item = EvidenceItem(
            control_id=control_id,
            evidence_type=evidence_type,
            content=content,
            description=description,
            source=source,
            collected_by=collected_by
        )

        collection.add_evidence(evidence_item)
        self._save_collection(collection)

        return evidence_item.id

    def get_evidence_for_control(self, control_id: str) -> list[EvidenceItem]:
        """Get evidence for a control from active collection"""
        collection = self.get_active_collection()
        if collection:
            return collection.get_evidence_for_control(control_id)
        return []

    def search_evidence(self,
                       control_id: str | None = None,
                       evidence_type: EvidenceType | None = None,
                       status: EvidenceStatus | None = None) -> list[EvidenceItem]:
        """Search evidence across active collection"""
        collection = self.get_active_collection()
        if not collection:
            return []

        results = []
        for control_evidence in collection.evidence_items.values():
            for evidence in control_evidence:
                if control_id and evidence.control_id != control_id.upper():
                    continue
                if evidence_type and evidence.evidence_type != evidence_type:
                    continue
                if status and evidence.status != status:
                    continue
                results.append(evidence)

        return results

    def get_collection_summary(self, collection_id: str | None = None) -> dict[str, Any] | None:
        """Get summary for a collection (or active if not specified)"""
        collection = None
        if collection_id and collection_id in self.collections:
            collection = self.collections[collection_id]
        elif not collection_id:
            collection = self.get_active_collection()

        return collection.get_summary() if collection else None

    def list_collections(self) -> dict[str, dict[str, Any]]:
        """List all collections with basic info"""
        return {
            collection_id: {
                "name": collection.name,
                "description": collection.description,
                "total_controls": len(collection.evidence_items),
                "total_evidence": sum(len(items) for items in collection.evidence_items.values())
            }
            for collection_id, collection in self.collections.items()
        }

    def export_collection(self, collection_id: str, format: str = "json") -> dict[str, Any] | None:
        """Export collection data"""
        collection = self.collections.get(collection_id)
        if collection:
            if format == "json":
                return collection.to_dict()
            else:
                logger.error(f"Unsupported export format: {format}")
        return None

    def _save_collection(self, collection: EvidenceCollection) -> None:
        """Save collection to file"""
        try:
            collection_file = self.storage_path / f"{collection.id}.json"
            with open(collection_file, 'w', encoding='utf-8') as f:
                json.dump(collection.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save collection {collection.id}: {e}")


# Global evidence manager instance
evidence_manager = EvidenceManager()
