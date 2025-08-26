#!/usr/bin/env python3
"""
Zerodha Kite MCP Server - Minimal Version
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ServerCapabilities
)
from pydantic import AnyUrl

try:
    from kiteconnect import KiteConnect
except ImportError:
    raise ImportError("Please install kiteconnect: pip install kiteconnect")

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='[%(asctime)s] [%(levelname)s] - %(message)s')
logger = logging.getLogger("kite-mcp-server")

CONFIG = {
    "SERVER_NAME": "kite-mcp-server",
    "SERVER_VERSION": "1.0.0",
    "MAX_INSTRUMENTS": 100,
}

class KiteMCPServer:
    def __init__(self):
        self.server = Server(CONFIG["SERVER_NAME"])
        self.kite: Optional[KiteConnect] = None
        self.api_key: Optional[str] = None
        self.access_token: Optional[str] = None
        self.is_configured = False
        self._setup_handlers()
        logger.info(f" {CONFIG['SERVER_NAME']} v{CONFIG['SERVER_VERSION']} initialized")

    def _setup_handlers(self):
        self._register_resources()
        self._register_tools()

    def _register_resources(self):
        @self.server.list_resources()
        async def list_kite_resources() -> List[Resource]:
            return [
                Resource(uri=AnyUrl("kite://profile"), name="User Profile", description="Get user profile", mimeType="application/json"),
                Resource(uri=AnyUrl("kite://portfolio"), name="Portfolio Holdings", description="Get holdings", mimeType="application/json"),
                Resource(uri=AnyUrl("kite://positions"), name="Trading Positions", description="Get positions", mimeType="application/json"),
                Resource(uri=AnyUrl("kite://orders"), name="Order Book", description="Get order book", mimeType="application/json"),
                Resource(uri=AnyUrl("kite://funds"), name="Account Funds", description="Get funds", mimeType="application/json"),
                Resource(uri=AnyUrl("kite://gtt-orders"), name="GTT Orders", description="Get active GTT orders", mimeType="application/json"),
            ]

        @self.server.read_resource()
        async def read_kite_resource(uri: AnyUrl) -> str:
            if not self._check_kite_connection():
                raise ValueError(" Kite Connect not configured. Use configure_kite tool first.")
            uri_str = str(uri)
            try:
                resource_data = await self._fetch_resource_data(uri_str)
                return json.dumps(resource_data, indent=2, default=str)
            except Exception as e:
                logger.error(f" Error reading {uri_str}: {e}")
                raise ValueError(f"Failed to read resource {uri_str}: {e}")

    async def _fetch_resource_data(self, uri: str) -> Dict[str, Any]:
        if uri == "kite://profile":
            return await asyncio.to_thread(self.kite.profile)
        elif uri == "kite://portfolio":
            return await asyncio.to_thread(self.kite.holdings)
        elif uri == "kite://positions":
            return await asyncio.to_thread(self.kite.positions)
        elif uri == "kite://orders":
            return await asyncio.to_thread(self.kite.orders)
        elif uri == "kite://funds":
            return await asyncio.to_thread(self.kite.margins)
        elif uri == "kite://gtt-orders":
            return await asyncio.to_thread(self.kite.gtts)
        else:
            raise ValueError(f"Unknown resource URI: {uri}")

    def _register_tools(self):
        @self.server.list_tools()
        async def list_kite_tools() -> List[Tool]:
            tools = [
                Tool(
                    name="configure_kite",
                    description="Configure Kite Connect API credentials",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "api_key": {"type": "string"},
                            "access_token": {"type": "string"}
                        },
                        "required": ["api_key", "access_token"]
                    },
                ),
                Tool(
                    name="get_quote",
                    description="Get real-time market quotes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instruments": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["instruments"]
                    },
                ),
                Tool(
                    name="place_order",
                    description="Place a new trading order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tradingsymbol": {"type": "string"},
                            "exchange": {"type": "string"},
                            "transaction_type": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "product": {"type": "string"},
                            "order_type": {"type": "string"},
                            "price": {"type": "number"},
                            "trigger_price": {"type": "number"},
                            "variety": {"type": "string", "default": "regular"},
                        },
                        "required": ["tradingsymbol", "exchange", "transaction_type", "quantity", "product", "order_type"]
                    },
                ),
                Tool(
                    name="modify_order",
                    description="Modify an existing order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "price": {"type": "number"},
                            "order_type": {"type": "string"},
                        },
                        "required": ["order_id"]
                    },
                ),
                Tool(
                    name="cancel_order",
                    description="Cancel an existing order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string"}
                        },
                        "required": ["order_id"]
                    },
                ),
                Tool(
                    name="get_holdings",
                    description="Get your current portfolio holdings",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                ),
                Tool(
                    name="get_gtt_orders",
                    description="Get active GTT (Good Till Triggered) orders",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                ),
            ]
            logger.info(f"Tools being returned: {[tool.name for tool in tools]}")
            return tools

        @self.server.call_tool()
        async def call_kite_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Received call_tool request for '{name}' with args: {arguments}")
            try:
                if name == "configure_kite":
                    return await self._configure_kite(arguments)
                elif name == "get_quote":
                    return await self._get_quote(arguments)
                elif name == "place_order":
                    return await self._place_order(arguments)
                elif name == "modify_order":
                    return await self._modify_order(arguments)
                elif name == "cancel_order":
                    return await self._cancel_order(arguments)
                elif name == "get_holdings":
                    return await self._get_holdings(arguments)
                elif name == "get_gtt_orders":
                    return await self._get_gtt_orders(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f" Tool {name} failed: {e}")
                return [TextContent(type="text", text=f" Tool '{name}' failed: {e}")]

    def _check_kite_connection(self) -> bool:
        return self.kite is not None and self.is_configured

    async def _configure_kite(self, arguments: Dict[str, Any]) -> List[TextContent]:
        logger.info("Attempting to configure Kite Connect...")
        try:
            self.api_key = arguments["api_key"]
            self.access_token = arguments["access_token"]
            
            logger.info("Initializing KiteConnect object...")
            self.kite = await asyncio.to_thread(KiteConnect, api_key=self.api_key)
            logger.info("KiteConnect object initialized.")

            logger.info("Setting access token...")
            await asyncio.to_thread(self.kite.set_access_token, self.access_token)
            logger.info("Access token set.")

            logger.info("Fetching user profile...")
            profile = await asyncio.to_thread(self.kite.profile)
            logger.info(f"User profile fetched: {profile.get('user_id')}")

            self.is_configured = True
            logger.info("Kite configuration successful.")
            return [
                TextContent(
                    type="text",
                    text=f" Kite Connect configured successfully!\nUser: {profile.get('user_name', 'N/A')}"
                )
            ]
        except Exception as e:
            logger.error(f"Error configuring Kite: {e}", exc_info=True)
            self.is_configured = False
            return [TextContent(type="text", text=f" Error configuring Kite: {e}")]

    async def _get_quote(self, arguments: Dict[str, Any]) -> List[TextContent]:
        if not self.kite:
            return [TextContent(type="text", text=" Kite not configured.")]
        try:
            instruments = arguments["instruments"]
            quotes = await asyncio.to_thread(self.kite.quote, instruments)
            return [
                TextContent(
                    type="text",
                    text=f" Real-time Quotes:\n```json\n{json.dumps(quotes, indent=2)}\n```"
                )
            ]
        except Exception as e:
            logger.error(f"Error getting quotes: {e}")
            return [TextContent(type="text", text=f" Error getting quotes: {e}")]

    async def _place_order(self, arguments: Dict[str, Any]) -> List[TextContent]:
        if not self.kite:
            return [TextContent(type="text", text=" Kite not configured.")]
        try:
            order_params = {
                "tradingsymbol": arguments["tradingsymbol"],
                "exchange": arguments["exchange"],
                "transaction_type": arguments["transaction_type"],
                "quantity": arguments["quantity"],
                "product": arguments["product"],
                "order_type": arguments["order_type"],
                "variety": arguments.get("variety", "regular"),
            }
            if "price" in arguments:
                order_params["price"] = arguments["price"]
            if "trigger_price" in arguments:
                order_params["trigger_price"] = arguments["trigger_price"]
            order_id = await asyncio.to_thread(self.kite.place_order, **order_params)
            return [
                TextContent(
                    type="text",
                    text=f" Order placed successfully!\nOrder ID: {order_id}"
                )
            ]
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return [TextContent(type="text", text=f" Error placing order: {e}")]

    async def _modify_order(self, arguments: Dict[str, Any]) -> List[TextContent]:
        if not self.kite:
            return [TextContent(type="text", text=" Kite not configured.")]
        try:
            order_id = arguments["order_id"]
            params = {k: v for k, v in arguments.items() if k != "order_id"}
            result = await asyncio.to_thread(self.kite.modify_order, order_id=order_id, **params)
            return [
                TextContent(
                    type="text",
                    text=f" Order modified successfully!\nOrder ID: {order_id}"
                )
            ]
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            return [TextContent(type="text", text=f" Error modifying order: {e}")]

    async def _cancel_order(self, arguments: Dict[str, Any]) -> List[TextContent]:
        if not self.kite:
            return [TextContent(type="text", text=" Kite not configured.")]
        try:
            order_id = arguments["order_id"]
            await asyncio.to_thread(self.kite.cancel_order, order_id=order_id)
            return [
                TextContent(
                    type="text",
                    text=f" Order cancelled successfully!\nOrder ID: {order_id}"
                )
            ]
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return [TextContent(type="text", text=f" Error cancelling order: {e}")]

    async def _get_holdings(self, arguments: Dict[str, Any]) -> List[TextContent]:
        if not self.kite:
            return [TextContent(type="text", text=" Kite not configured.")]
        try:
            holdings = await asyncio.to_thread(self.kite.holdings)
            return [
                TextContent(
                    type="text",
                    text=f" Current Holdings:\n```json\n{json.dumps(holdings, indent=2)}\n```"
                )
            ]
        except Exception as e:
            logger.error(f"Error getting holdings: {e}")
            return [TextContent(type="text", text=f" Error getting holdings: {e}")]

    async def _get_gtt_orders(self, arguments: Dict[str, Any]) -> List[TextContent]:
        if not self._check_kite_connection():
            return [TextContent(type="text", text=" Kite Connect not configured. Use configure_kite tool first.")]
        try:
            gtt_orders = await asyncio.to_thread(self.kite.gtts)
            if not gtt_orders:
                return [TextContent(type="text", text="No active GTT orders found.")]
            
            return [
                TextContent(
                    type="text",
                    text=f" Active GTT Orders:\n```json\n{json.dumps(gtt_orders, indent=2, default=str)}\n```"
                )
            ]
        except Exception as e:
            logger.error(f"Error getting GTT orders: {e}")
            return [TextContent(type="text", text=f" Failed to retrieve GTT orders: {e}")]

class NotificationOptions:
    def __init__(self, logging_level="INFO", resources_changed=False, tools_changed=False):
        self.logging_level = logging_level
        self.resources_changed = resources_changed
        self.tools_changed = tools_changed

async def main():
    server_instance = KiteMCPServer()
    async with AsyncExitStack() as stack:
        streams = await stack.enter_async_context(stdio_server())
        caps = server_instance.server.get_capabilities(
            notification_options=NotificationOptions(logging_level="INFO"),
            experimental_capabilities={}
        )
        capabilities = ServerCapabilities.model_validate(caps)
        await server_instance.server.run(
            streams[0],
            streams[1],
            InitializationOptions(
                server_name=CONFIG["SERVER_NAME"],
                server_version=CONFIG["SERVER_VERSION"],
                capabilities=capabilities
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
