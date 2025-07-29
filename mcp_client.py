import asyncio
import json
import subprocess
import os
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self):
        self.process = None
        self.reader = None
        self.writer = None
        self.request_id = 0
        
    async def start_server(self):
        """Start the MCP Google Drive server"""
        try:
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                "node", "./mcp-gdrive/dist/index.js",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            self.reader = self.process.stdout
            self.writer = self.process.stdin
            
            # Initialize the connection
            await self._send_initialize()
            return True
            
        except Exception as e:
            logger.error(f"Error starting MCP server: {e}")
            return False
    
    async def _send_initialize(self):
        """Send initialize request to MCP server"""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "Sara Slack Bot",
                    "version": "1.0.0"
                }
            }
        }
        
        await self._send_request(init_request)
        response = await self._read_response()
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await self._send_request(initialized_notification)
    
    def _next_id(self):
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def _send_request(self, request: Dict[str, Any]):
        """Send a request to the MCP server"""
        if not self.writer:
            raise Exception("MCP server not started")
        
        request_json = json.dumps(request) + "\n"
        self.writer.write(request_json.encode())
        await self.writer.drain()
    
    async def _read_response(self) -> Optional[Dict[str, Any]]:
        """Read a response from the MCP server"""
        if not self.reader:
            return None
        
        try:
            line = await self.reader.readline()
            if line:
                return json.loads(line.decode().strip())
            return None
        except Exception as e:
            logger.error(f"Error reading response: {e}")
            return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call a tool on the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        await self._send_request(request)
        return await self._read_response()
    
    async def list_tools(self) -> Optional[Dict[str, Any]]:
        """List available tools"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list"
        }
        
        await self._send_request(request)
        return await self._read_response()
    
    async def search_sheets(self, query: str) -> Optional[str]:
        """Search for Google Sheets files"""
        response = await self.call_tool("gdrive_search", {
            "query": f"{query} type:spreadsheet"
        })
        
        if response and not response.get("error"):
            result = response.get("result", {})
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "")
        return None
    
    async def read_sheet_data(self, spreadsheet_id: str, ranges: Optional[List[str]] = None, try_public_first: bool = True) -> Optional[str]:
        """Read data from a Google Sheet, trying public access first if enabled"""
        arguments = {"spreadsheetId": spreadsheet_id}
        if ranges:
            arguments["ranges"] = ranges
        
        # Try public access first for sheets that might be publicly accessible
        if try_public_first:
            try:
                response = await self.call_tool("gsheets_read_public", arguments)
                if response and not response.get("error"):
                    result = response.get("result", {})
                    content = result.get("content", [])
                    if content and len(content) > 0:
                        return content[0].get("text", "")
            except Exception as e:
                logger.info(f"Public access failed, trying authenticated access: {e}")
        
        # Fall back to authenticated access
        response = await self.call_tool("gsheets_read", arguments)
        
        if response and not response.get("error"):
            result = response.get("result", {})
            content = result.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "")
        return None
    
    async def cleanup(self):
        """Clean up the MCP server process"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        
        if self.process:
            self.process.terminate()
            await self.process.wait()

# Global instance
mcp_client = MCPClient()
