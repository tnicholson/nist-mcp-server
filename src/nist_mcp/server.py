#!/usr/bin/env python3
"""NIST MCP Server - Main server implementation"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from mcp.server import FastMCP

from .data.loader import NISTDataLoader
from .endpoints.control_endpoints import register_control_endpoints
from .endpoints.analysis_endpoints import register_analysis_endpoints
from .endpoints.framework_endpoints import register_framework_endpoints
from .endpoints.monitoring_endpoints import register_monitoring_endpoints

logger = logging.getLogger(__name__)


class NISTMCPServer:
    """Main NIST MCP Server implementation"""

    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data"
        self.data_path = data_path
        self.loader = NISTDataLoader(self.data_path)
        logger.info(f"NIST MCP Server initialized with data path: {data_path}")


nist_server = NISTMCPServer()


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    # Initialize data loader
    await nist_server.loader.initialize()

    # Initialize dependency injection container with correct data path
    from .infrastructure.container import DependencyContainer, AppConfig
    config = AppConfig(data_path=nist_server.data_path)
    container = DependencyContainer(config)
    await container.initialize()

    # Set as global container for service access
    from .infrastructure.container import set_container
    set_container(container)

    # Register all endpoint modules (async now for control endpoints)
    await register_control_endpoints(app, nist_server.loader)
    register_analysis_endpoints(app, nist_server.loader)
    register_framework_endpoints(app, nist_server.loader)
    register_monitoring_endpoints(app, nist_server.loader)

    yield

    # Cleanup on shutdown
    await container.shutdown()


# Create MCP server
app = FastMCP("nist-mcp-server", lifespan=lifespan)


def main() -> None:
    """Entry point for the MCP server"""
    app.run()


if __name__ == "__main__":
    main()
