#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - MCP Connectors
Extended MCP connectors for 3rd party tools
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp


class MCPConnector:
    """Base MCP connector class."""
    
    def __init__(self, name: str, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.name = name
        self.config = config
        self.logger = logger or logging.getLogger(f"MCP-{name}")
        self.base_url = config.get("mcp_url", "")
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "GEM-OS/2.0.0 MCP-Client",
            "Accept": "application/json",
            **config.get("headers", {})
        }
    
    async def initialize(self) -> bool:
        """Initialize MCP connection."""
        try:
            self.session = aiohttp.ClientSession()
            self.connected = True
            self.logger.info(f"✅ {self.name} MCP connector initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name} MCP: {e}")
            return False
    
    async def call_method(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call MCP method."""
        if not self.connected:
            return None
            
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            
            async with self.session.post(self.base_url, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"{self.name} MCP call failed: {e}")
        return None
    
    async def shutdown(self):
        """Close MCP connection."""
        if self.session:
            await self.session.close()
        self.connected = False


class GitBookConnector(MCPConnector):
    """GitBook MCP connector with API integration."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        super().__init__("GitBook", config, logger)
        self.organization_id = config.get("organization_id", "")
        self.openapi_spec = config.get("openapi_spec", "")
    
    async def search_docs(self, query: str) -> List[Dict[str, Any]]:
        """Search GitBook documentation."""
        result = await self.call_method("search", {
            "query": query,
            "organization": self.organization_id,
            "limit": self.config.get("max_search_results", 5)
        })
        return result.get("result", []) if result else []
    
    async def get_page_content(self, page_id: str) -> Optional[str]:
        """Get page content from GitBook."""
        result = await self.call_method("get_page", {
            "page_id": page_id,
            "organization": self.organization_id
        })
        return result.get("result", {}).get("content", "") if result else None
    
    async def publish_openapi_spec(self, spec_path: str) -> bool:
        """Publish OpenAPI specification to GitBook."""
        try:
            result = await self.call_method("openapi_publish", {
                "spec": self.openapi_spec,
                "organization": self.organization_id,
                "spec_path": spec_path
            })
            return result.get("result", {}).get("success", False) if result else False
        except Exception as e:
            self.logger.error(f"Failed to publish OpenAPI spec: {e}")
            return False


class SlackConnector(MCPConnector):
    """Slack MCP connector."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        super().__init__("Slack", config, logger)
    
    async def send_message(self, channel: str, message: str) -> bool:
        """Send message to Slack channel."""
        result = await self.call_method("send_message", {
            "channel": channel,
            "text": message
        })
        return result.get("result", {}).get("ok", False) if result else False
    
    async def get_messages(self, channel: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get messages from Slack channel."""
        result = await self.call_method("get_messages", {
            "channel": channel,
            "limit": limit
        })
        return result.get("result", {}).get("messages", []) if result else []


class GoogleDriveConnector(MCPConnector):
    """Google Drive MCP connector."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        super().__init__("GoogleDrive", config, logger)
    
    async def search_files(self, query: str) -> List[Dict[str, Any]]:
        """Search files in Google Drive."""
        result = await self.call_method("search_files", {
            "query": query,
            "limit": self.config.get("max_search_results", 10)
        })
        return result.get("result", {}).get("files", []) if result else []
    
    async def get_file_content(self, file_id: str) -> Optional[str]:
        """Get file content from Google Drive."""
        result = await self.call_method("get_file", {
            "file_id": file_id
        })
        return result.get("result", {}).get("content", "") if result else None


class MCPConnectorManager:
    """Manager for all MCP connectors."""
    
    def __init__(self, config_manager, logger: Optional[logging.Logger] = None):
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger("MCPConnectorManager")
        self.connectors: Dict[str, MCPConnector] = {}
    
    async def initialize(self) -> bool:
        """Initialize all MCP connectors."""
        try:
            # Initialize GitBook connector
            gitbook_config = self.config_manager.get_integration_config("gitbook", {})
            if gitbook_config.get("enabled", False):
                gitbook_connector = GitBookConnector(gitbook_config, self.logger)
                if await gitbook_connector.initialize():
                    self.connectors["gitbook"] = gitbook_connector
            
            # Initialize Slack connector
            slack_config = self.config_manager.get_integration_config("slack", {})
            if slack_config.get("enabled", False):
                slack_connector = SlackConnector(slack_config, self.logger)
                if await slack_connector.initialize():
                    self.connectors["slack"] = slack_connector
            
            # Initialize Google Drive connector
            gdrive_config = self.config_manager.get_integration_config("google_drive", {})
            if gdrive_config.get("enabled", False):
                gdrive_connector = GoogleDriveConnector(gdrive_config, self.logger)
                if await gdrive_connector.initialize():
                    self.connectors["google_drive"] = gdrive_connector
            
            self.logger.info(f"✅ Initialized {len(self.connectors)} MCP connectors")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP connectors: {e}")
            return False
    
    def get_connector(self, name: str) -> Optional[MCPConnector]:
        """Get MCP connector by name."""
        return self.connectors.get(name)
    
    async def handle_voice_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice commands for MCP connectors."""
        command_lower = command.lower()
        
        # GitBook commands
        if any(word in command_lower for word in ["gitbook", "docs", "documentation"]):
            gitbook = self.get_connector("gitbook")
            if gitbook and isinstance(gitbook, GitBookConnector):
                if "search" in command_lower:
                    query = params.get("query", "")
                    results = await gitbook.search_docs(query)
                    if results:
                        titles = [r.get("title", "Untitled") for r in results[:3]]
                        return {"response": f"Found {len(results)} docs: {', '.join(titles)}"}
                    return {"response": f"No documentation found for '{query}'"}
        
        # Slack commands
        elif any(word in command_lower for word in ["slack", "message", "chat"]):
            slack = self.get_connector("slack")
            if slack and isinstance(slack, SlackConnector):
                if "send" in command_lower:
                    channel = params.get("channel", "#general")
                    message = params.get("message", "")
                    success = await slack.send_message(channel, message)
                    return {"response": "Message sent!" if success else "Failed to send message"}
        
        # Google Drive commands
        elif any(word in command_lower for word in ["drive", "google", "file"]):
            gdrive = self.get_connector("google_drive")
            if gdrive and isinstance(gdrive, GoogleDriveConnector):
                if "search" in command_lower:
                    query = params.get("query", "")
                    files = await gdrive.search_files(query)
                    if files:
                        names = [f.get("name", "Untitled") for f in files[:3]]
                        return {"response": f"Found {len(files)} files: {', '.join(names)}"}
                    return {"response": f"No files found for '{query}'"}
        
        return {"response": "I can help with GitBook docs, Slack messages, or Google Drive files. What would you like to do?"}
    
    async def shutdown(self):
        """Shutdown all MCP connectors."""
        for connector in self.connectors.values():
            await connector.shutdown()
        self.connectors.clear()