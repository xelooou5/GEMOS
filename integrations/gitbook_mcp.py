#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - GitBook MCP Integration
Connect to GitBook via Model Context Protocol
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp


class GitBookMCPClient:
    """GitBook MCP client for GEM OS integration."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("GitBookMCP")
        self.base_url = config.get("mcp_url", "https://mcp.gitbook.com")
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
    
    async def initialize(self) -> bool:
        """Initialize GitBook MCP connection."""
        try:
            self.session = aiohttp.ClientSession()
            self.connected = True
            self.logger.info("✅ Connected to GitBook MCP")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to GitBook MCP: {e}")
            return False
    
    async def search_content(self, query: str) -> List[Dict[str, Any]]:
        """Search content in GitBook."""
        if not self.connected:
            return []
            
        try:
            payload = {
                "method": "search",
                "params": {"query": query}
            }
            
            async with self.session.post(self.base_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", [])
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
        return []
    
    async def get_page(self, page_id: str) -> Optional[str]:
        """Get page content from GitBook."""
        if not self.connected:
            return None
            
        try:
            payload = {
                "method": "get_page",
                "params": {"page_id": page_id}
            }
            
            async with self.session.post(self.base_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", {}).get("content", "")
        except Exception as e:
            self.logger.error(f"Failed to get page: {e}")
        return None
    
    async def shutdown(self):
        """Close MCP connection."""
        if self.session:
            await self.session.close()
        self.connected = False


class GitBookIntegration:
    """GitBook integration for GEM OS."""
    
    def __init__(self, config_manager, logger: Optional[logging.Logger] = None):
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger("GitBookIntegration")
        self.mcp_client: Optional[GitBookMCPClient] = None
        
    async def initialize(self) -> bool:
        """Initialize GitBook integration."""
        try:
            gitbook_config = self.config_manager.get_integration_config("gitbook", {})
            self.mcp_client = GitBookMCPClient(gitbook_config, self.logger)
            
            if await self.mcp_client.initialize():
                self.logger.info("✅ GitBook integration initialized")
                return True
            else:
                self.logger.warning("❌ Failed to initialize GitBook MCP")
                return False
        except Exception as e:
            self.logger.error(f"GitBook integration error: {e}")
            return False
    
    async def handle_voice_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice commands for GitBook."""
        if not self.mcp_client or not self.mcp_client.connected:
            return {"error": "GitBook not connected"}
        
        command_lower = command.lower()
        
        if "search" in command_lower or "find" in command_lower:
            query = params.get("query", "")
            if not query:
                return {"response": "What would you like to search for in GitBook?"}
            
            results = await self.mcp_client.search_content(query)
            if results:
                titles = [r.get("title", "Untitled") for r in results[:3]]
                return {"response": f"Found {len(results)} results: {', '.join(titles)}"}
            else:
                return {"response": f"No results found for '{query}'"}
        
        elif "read" in command_lower or "open" in command_lower:
            page_title = params.get("page", "")
            if not page_title:
                return {"response": "Which page would you like me to read?"}
            
            results = await self.mcp_client.search_content(page_title)
            if results:
                page_id = results[0].get("id")
                content = await self.mcp_client.get_page(page_id)
                if content:
                    summary = content[:200] + "..." if len(content) > 200 else content
                    return {"response": f"Here's the content: {summary}"}
            
            return {"response": f"Couldn't find page '{page_title}'"}
        
        return {"response": "I can help you search or read GitBook content. What would you like to do?"}
    
    async def shutdown(self):
        """Shutdown GitBook integration."""
        if self.mcp_client:
            await self.mcp_client.shutdown()