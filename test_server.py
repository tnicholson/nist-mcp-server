#!/usr/bin/env python3
"""
Simple test script for the NIST MCP server
"""

import asyncio
import json
import subprocess
import sys
from typing import Dict, Any

async def test_mcp_server():
    """Test the MCP server by sending initialize and tool calls"""

    # Start the server process
    process = await asyncio.create_subprocess_exec(
        'nist-mcp',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    async def send_request(request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and get response"""
        request_json = json.dumps(request) + '\n'
        process.stdin.write(request_json.encode())
        await process.stdin.drain()

        # Read response
        response_line = await process.stdout.readline()
        response = json.loads(response_line.decode().strip())
        return response

    try:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        print("Sending initialize request...")
        init_response = await send_request(init_request)
        print(f"Initialize response: {json.dumps(init_response, indent=2)}")

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        process.stdin.write((json.dumps(initialized_notification) + '\n').encode())
        await process.stdin.drain()
        print("Sent initialized notification")

        # List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        print("Listing tools...")
        tools_response = await send_request(tools_request)
        print(f"Tools response: {json.dumps(tools_response, indent=2)}")

        # Call list_controls tool
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_controls",
                "arguments": {}
            }
        }

        print("Calling list_controls tool...")
        call_response = await send_request(call_request)
        print(f"Tool call response: {json.dumps(call_response, indent=2)}")

    finally:
        # Terminate the process
        process.terminate()
        await process.wait()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
