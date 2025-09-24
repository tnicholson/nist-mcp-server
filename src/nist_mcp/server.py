#!/usr/bin/env python3
"""
NIST MCP Server - Main server implementation
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List

from mcp.server import FastMCP

from .data.loader import NISTDataLoader

logger = logging.getLogger(__name__)


class NISTMCPServer:
    """Main NIST MCP Server implementation"""

    def __init__(self, data_path: Path = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent.parent / "data"
        self.data_path = data_path
        self.loader = NISTDataLoader(self.data_path)
        logger.info(f"NIST MCP Server initialized with data path: {data_path}")

    async def list_nist_controls(self) -> List[Dict[str, Any]]:
        """List available NIST controls"""
        try:
            controls_data = await self.loader.load_controls()
            controls = controls_data.get("catalog", {}).get("controls", [])
            return [
                {"id": control["id"], "title": control["title"]} for control in controls
            ]
        except Exception as e:
            logger.error(f"Error loading controls: {e}")
            return []

    async def get_control_details(self, control_id: str) -> Dict[str, Any]:
        """Get details for a specific control"""
        try:
            controls_data = await self.loader.load_controls()
            control = self.loader.get_control_by_id(controls_data, control_id)
            if control:
                return control
            else:
                raise ValueError(f"Control {control_id} not found")
        except Exception as e:
            logger.error(f"Error getting control {control_id}: {e}")
            raise


nist_server = NISTMCPServer()


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    await nist_server.loader.initialize()
    yield


# Create MCP server
app = FastMCP("nist-mcp-server", lifespan=lifespan)


@app.tool()
async def list_controls() -> List[Dict[str, Any]]:
    """List all available NIST controls"""
    return await nist_server.list_nist_controls()


@app.tool()
async def get_control(control_id: str) -> Dict[str, Any]:
    """Get details for a specific NIST control"""
    return await nist_server.get_control_details(control_id)


def main():
    """Entry point for the MCP server"""
    app.run()


if __name__ == "__main__":
    main()
