#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Notion MCP Integration
Connect to Notion workspace via Model Context Protocol
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from pathlib import Path


class NotionMCPClient:
    """Notion MCP client for GEM OS integration."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("NotionMCP")
        self.base_url = "https://mcp.notion.com/mcp"
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "GEM-OS/2.0.0 MCP-Client",
            "Accept": "application/json",
            **config.get("headers", {})
        }
    
    async def initialize(self) -> bool:
        """Initialize Notion MCP connection."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{self.base_url}/health", headers=self.headers) as response:
                if response.status == 200:
                    self.connected = True
                    self.logger.info("✅ Connected to Notion MCP")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to connect to Notion MCP: {e}")
            
        return False
    
    async def search_pages(self, query: str) -> List[Dict[str, Any]]:
        """Search pages in Notion workspace."""
        if not self.connected:
            return []
            
        try:
            payload = {
                "method": "search_pages",
                "params": {"query": query}
            }
            
            async with self.session.post(self.base_url, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", [])
                    
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            
        return []
    
    async def get_page_content(self, page_id: str) -> Optional[str]:
        """Get content from a Notion page."""
        if not self.connected:
            return None
            
        try:
            payload = {
                "method": "get_page",
                "params": {"page_id": page_id}
            }
            
            async with self.session.post(self.base_url, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", {}).get("content", "")
                    
        except Exception as e:
            self.logger.error(f"Failed to get page content: {e}")
            
        return None
    
    async def create_page(self, title: str, content: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Create a new page in Notion."""
        if not self.connected:
            return None
            
        try:
            payload = {
                "method": "create_page",
                "params": {
                    "title": title,
                    "content": content,
                    "parent_id": parent_id
                }
            }
            
            async with self.session.post(self.base_url, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result", {}).get("id")
                    
        except Exception as e:
            self.logger.error(f"Failed to create page: {e}")
            
        return None
    
    async def shutdown(self):
        """Close the MCP connection."""
        if self.session:
            await self.session.close()
        self.connected = False


class NotionIntegration:
    """Main Notion integration for GEM OS."""
    
    def __init__(self, config_manager, logger: Optional[logging.Logger] = None):
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger("NotionIntegration")
        self.mcp_client: Optional[NotionMCPClient] = None
        
    async def initialize(self) -> bool:
        """Initialize Notion integration."""
        try:
            notion_config = self.config_manager.get_integration_config("notion", {})
            
            self.mcp_client = NotionMCPClient(notion_config, self.logger)
            
            if await self.mcp_client.initialize():
                self.logger.info("✅ Notion integration initialized")
                return True
            else:
                self.logger.warning("❌ Failed to initialize Notion MCP")
                return False
                
        except Exception as e:
            self.logger.error(f"Notion integration error: {e}")
            return False
    
    async def handle_voice_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice commands for Notion."""
        if not self.mcp_client or not self.mcp_client.connected:
            return {"error": "Notion not connected"}
        
        command_lower = command.lower()
        
        if "search" in command_lower or "find" in command_lower:
            query = params.get("query", "")
            if not query:
                return {"response": "What would you like to search for in Notion?"}
            
            pages = await self.mcp_client.search_pages(query)
            if pages:
                titles = [page.get("title", "Untitled") for page in pages[:3]]
                return {"response": f"Found {len(pages)} pages: {', '.join(titles)}"}
            else:
                return {"response": f"No pages found for '{query}'"}
        
        elif "create" in command_lower or "new" in command_lower:
            title = params.get("title", "")
            content = params.get("content", "")
            
            if not title:
                return {"response": "What should I title the new page?"}
            
            page_id = await self.mcp_client.create_page(title, content)
            if page_id:
                return {"response": f"Created new page: {title}"}
            else:
                return {"response": "Failed to create page"}
        
        elif "read" in command_lower or "open" in command_lower:
            page_title = params.get("page", "")
            if not page_title:
                return {"response": "Which page would you like me to read?"}
            
            # Search for the page first
            pages = await self.mcp_client.search_pages(page_title)
            if pages:
                page_id = pages[0].get("id")
                content = await self.mcp_client.get_page_content(page_id)
                if content:
                    # Truncate for voice response
                    summary = content[:200] + "..." if len(content) > 200 else content
                    return {"response": f"Here's the content: {summary}"}
            
            return {"response": f"Couldn't find page '{page_title}'"}
        
        return {"response": "I can help you search, create, or read Notion pages. What would you like to do?"}
    
    async def shutdown(self):
        """Shutdown Notion integration."""
        if self.mcp_client:
            await self.mcp_client.shutdown()