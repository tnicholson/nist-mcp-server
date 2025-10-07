"""Dependency Injection Container for NIST MCP Server"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from ..data.loader import NISTDataLoader
from ..history.storage import HistoricalStorage
from ..monitoring.monitor import ControlMonitor
from ..workflows.strands import StrandsOrchestrator
from ..services.control_service import ControlService
from ..connectors.base import connector_registry
from ..connectors.aws import AWSConnector

logger = logging.getLogger(__name__)


class IServiceRegistry(Protocol):
    """Protocol for service registry operations"""

    async def get_data_loader(self) -> NISTDataLoader:
        """Get the data loader service"""
        ...

    async def get_storage_service(self) -> HistoricalStorage:
        """Get the historical storage service"""
        ...

    async def get_monitor_service(self) -> ControlMonitor:
        """Get the control monitor service"""
        ...

    async def get_orchestrator_service(self) -> StrandsOrchestrator:
        """Get the workflow orchestrator service"""
        ...


class AppConfig:
    """Application configuration"""

    def __init__(
        self,
        data_path: Optional[Path] = None,
        enable_monitoring: bool = True,
        enable_workflows: bool = True,
        default_connector_type: str = "aws",
    ):
        self.data_path = data_path or (Path(__file__).parent.parent.parent / "data")
        self.enable_monitoring = enable_monitoring
        self.enable_workflows = enable_workflows
        self.default_connector_type = default_connector_type


class DependencyContainer:
    """Dependency Injection Container for NIST MCP Services"""

    def __init__(self, config: AppConfig):
        self.config = config
        self._services: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all services"""
        if self._initialized:
            return

        try:
            # Initialize data loader first
            self._services["data_loader"] = NISTDataLoader(self.config.data_path)
            await self._services["data_loader"].initialize()

            # Initialize control service
            self._services["control_service"] = ControlService(self._services["data_loader"])

            # Initialize storage service
            self._services["storage"] = HistoricalStorage()
            self._services["storage"].initialize()

            # Initialize monitor if enabled
            if self.config.enable_monitoring:
                self._services["monitor"] = ControlMonitor(self._services["storage"])

            # Initialize orchestrator if enabled
            if self.config.enable_workflows:
                self._services["orchestrator"] = StrandsOrchestrator(
                    storage=self._services["storage"],
                    monitor=self._services.get("monitor"),
                    data_loader=self._services["data_loader"]
                )

            # Register default connector types
            connector_registry.register_connector_type(
                self.config.default_connector_type,
                AWSConnector
            )

            self._initialized = True
            logger.info("Dependency container initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize dependency container: {e}")
            raise

    async def shutdown(self) -> None:
        """Cleanup all services"""
        try:
            # Shut down services in reverse order
            for service_name in ["orchestrator", "monitor", "storage"]:
                if service_name in self._services:
                    service = self._services[service_name]
                    if hasattr(service, 'shutdown'):
                        await service.shutdown()

            self._services.clear()
            self._initialized = False
            logger.info("Dependency container shut down successfully")

        except Exception as e:
            logger.error(f"Error during container shutdown: {e}")

    # Service accessors with lazy initialization and type safety

    async def get_data_loader(self) -> NISTDataLoader:
        """Get the NIST data loader service"""
        if not self._initialized:
            await self.initialize()
        return self._services["data_loader"]

    async def get_control_service(self) -> ControlService:
        """Get the control service"""
        if not self._initialized:
            await self.initialize()
        return self._services["control_service"]

    async def get_storage_service(self) -> HistoricalStorage:
        """Get the historical storage service"""
        if not self._initialized:
            await self.initialize()
        return self._services["storage"]

    async def get_monitor_service(self) -> ControlMonitor:
        """Get the control monitor service"""
        if not self._initialized:
            await self.initialize()
        if not self.config.enable_monitoring:
            raise ValueError("Monitoring service is disabled in configuration")
        return self._services["monitor"]

    async def get_orchestrator_service(self) -> StrandsOrchestrator:
        """Get the workflow orchestrator service"""
        if not self._initialized:
            await self.initialize()
        if not self.config.enable_workflows:
            raise ValueError("Workflow orchestrator is disabled in configuration")
        return self._services["orchestrator"]

    # Convenience methods for service checks

    async def is_monitoring_enabled(self) -> bool:
        """Check if monitoring services are enabled"""
        return self.config.enable_monitoring and "monitor" in self._services

    async def is_workflows_enabled(self) -> bool:
        """Check if workflow services are enabled"""
        return self.config.enable_workflows and "orchestrator" in self._services


# Global container instance for backward compatibility (temporary)
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global container instance (for backward compatibility)"""
    global _container
    if _container is None:
        # Default configuration
        config = AppConfig()
        _container = DependencyContainer(config)
    return _container


def set_container(container: DependencyContainer) -> None:
    """Set the global container instance"""
    global _container
    _container = container


# Factory functions for common configurations

def create_default_container() -> DependencyContainer:
    """Create a container with default configuration"""
    config = AppConfig()
    return DependencyContainer(config)


def create_minimal_container(data_path: Optional[Path] = None) -> DependencyContainer:
    """Create a container with minimal services (no monitoring/workflows)"""
    config = AppConfig(
        data_path=data_path,
        enable_monitoring=False,
        enable_workflows=False,
    )
    return DependencyContainer(config)
