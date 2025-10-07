"""Base connector classes for external system integrations

Provides interfaces for connecting to various external systems to gather
compliance evidence and perform automated checks.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base class for all connectors"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False
        self.connector_id = config.get("connector_id", self.__class__.__name__)
        self.name = config.get("name", self.connector_id)

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external system"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the external system"""
        pass

    @abstractmethod
    async def check_control(self, control_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a compliance check for a specific control"""
        pass

    @abstractmethod
    async def collect_evidence(self, control_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Collect evidence for a control from the external system"""
        pass

    def is_connected(self) -> bool:
        """Check if connector is currently connected"""
        return self.connected

    def get_status(self) -> Dict[str, Any]:
        """Get connector status information"""
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "type": self.__class__.__name__,
            "connected": self.connected,
            "config_keys": list(self.config.keys()) if self.config else []
        }


class APIConnector(BaseConnector):
    """Base class for API-based connectors"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "")
        self.api_key = config.get("api_key", "")
        self.headers = config.get("headers", {})
        self.session = None

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the API"""
        pass

    @abstractmethod
    async def make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Make an API request"""
        pass


class DatabaseConnector(BaseConnector):
    """Base class for database connectors"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_string = config.get("connection_string", "")
        self.connection = None

    @abstractmethod
    async def execute_query(self, query: str, parameters: Dict = None) -> List[Dict[str, Any]]:
        """Execute a database query"""
        pass


class FileSystemConnector(BaseConnector):
    """Base class for file system connectors"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_path = config.get("base_path", "/")
        self.permissions = config.get("permissions", {})

    @abstractmethod
    async def list_files(self, path: str, pattern: str = "*") -> List[str]:
        """List files in a directory"""
        pass

    @abstractmethod
    async def read_file(self, file_path: str) -> str:
        """Read content from a file"""
        pass

    @abstractmethod
    async def check_file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        pass


class CloudServiceConnector(BaseConnector):
    """Base class for cloud service connectors (AWS, Azure, GCP)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.region = config.get("region", "us-east-1")
        self.credentials = config.get("credentials", {})

    @abstractmethod
    async def get_resource_status(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Get status of a cloud resource"""
        pass

    @abstractmethod
    async def list_resources(self, resource_type: str, filters: Dict = None) -> List[Dict[str, Any]]:
        """List cloud resources"""
        pass


class ConnectorRegistry:
    """Registry for managing multiple connectors"""

    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        self.connector_types: Dict[str, type] = {}

    def register_connector_type(self, name: str, connector_class: type) -> None:
        """Register a connector type"""
        self.connector_types[name] = connector_class

    def create_connector(self, connector_type: str, config: Dict[str, Any]) -> Optional[BaseConnector]:
        """Create a connector instance"""
        if connector_type not in self.connector_types:
            logger.error(f"Unknown connector type: {connector_type}")
            return None

        try:
            connector_class = self.connector_types[connector_type]
            connector = connector_class(config)
            self.connectors[connector.connector_id] = connector
            return connector
        except Exception as e:
            logger.error(f"Failed to create connector {connector_type}: {e}")
            return None

    def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        """Get a connector by ID"""
        return self.connectors.get(connector_id)

    def list_connectors(self) -> List[Dict[str, Any]]:
        """List all registered connectors"""
        return [
            connector.get_status()
            for connector in self.connectors.values()
        ]

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all registered connectors"""
        results = {}
        for connector_id, connector in self.connectors.items():
            try:
                results[connector_id] = await connector.connect()
            except Exception as e:
                logger.error(f"Failed to connect {connector_id}: {e}")
                results[connector_id] = False

        return results

    async def disconnect_all(self) -> None:
        """Disconnect all connectors"""
        for connector in self.connectors.values():
            try:
                await connector.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {connector.connector_id}: {e}")


# Global connector registry
connector_registry = ConnectorRegistry()
