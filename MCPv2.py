import asyncio
import json
import sys 
from typing import Any, Dict, List
from contextlib import AsyncExitStack

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent, ServerCapabilities
from pydantic import AnyUrl

try:
    from kiteconnect import KiteConnect
except ImportError:
    raise ImportError("Install kiteconnect: pip install kiteconnect")

class KiteMCPServer:
    def __init__(self):
        self.server = Server("kite-mcp-server")
        self.kite = None
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_resources()
        async def list_resources():
            return [
                Resource(uri=AnyUrl("kite://portfolio"), name="Portfolio", description="Holdings", mimeType="application/json"),
                Resource(uri=AnyUrl("kite://positions"), name="Positions", description="Current positions", mimeType="application/json"),
                Resource(uri=AnyUrl("kite://orders"), name="Orders", description="Order book", mimeType="application/json"),
            ]

        @self.server.read_resource()
        async def read_resource(uri: AnyUrl):
            if not self.kite:
                raise ValueError("Configure Kite first")
            
            uri_map = {
                "kite://portfolio": self.kite.holdings,
                "kite://positions": self.kite.positions,
                "kite://orders": self.kite.orders,
            }
            
            data = await asyncio.to_thread(uri_map[str(uri)])
            return json.dumps(data, indent=2, default=str)

        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(name="configure", description="Set API credentials",
                     inputSchema={"type": "object", "properties": {"api_key": {"type": "string"}, "access_token": {"type": "string"}}, "required": ["api_key", "access_token"]}),
                Tool(name="quote", description="Get quotes",
                     inputSchema={"type": "object", "properties": {"symbols": {"type": "array", "items": {"type": "string"}}}, "required": ["symbols"]}),
                Tool(name="place_order", description="Place order",
                     inputSchema={"type": "object", "properties": {"symbol": {"type": "string"}, "exchange": {"type": "string"}, "transaction_type": {"type": "string"}, "quantity": {"type": "integer"}, "product": {"type": "string"}, "order_type": {"type": "string"}, "price": {"type": "number"}}, "required": ["symbol", "exchange", "transaction_type", "quantity", "product", "order_type"]}),
                Tool(name="get_holdings", description="Get portfolio holdings",
                     inputSchema={"type": "object", "properties": {}, "required": []}),
                Tool(name="get_gtt_orders", description="Get GTT orders",
                     inputSchema={"type": "object", "properties": {}, "required": []}),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            try:
                if name == "configure":
                    self.kite = KiteConnect(api_key=arguments["api_key"])
                    self.kite.set_access_token(arguments["access_token"])
                    profile = await asyncio.to_thread(self.kite.profile)
                    return [TextContent(type="text", text=f"Connected: {profile.get('user_name')}")]
                
                elif name == "quote":
                    if not self.kite:
                        return [TextContent(type="text", text="Configure first")]
                    quotes = await asyncio.to_thread(self.kite.quote, arguments["symbols"])
                    return [TextContent(type="text", text=f"Quotes:\n```json\n{json.dumps(quotes, indent=2)}\n```")]
                
                elif name == "place_order":
                    if not self.kite:
                        return [TextContent(type="text", text="Configure first")]
                    order_id = await asyncio.to_thread(self.kite.place_order, 
                        tradingsymbol=arguments["symbol"],
                        exchange=arguments["exchange"],
                        transaction_type=arguments["transaction_type"],
                        quantity=arguments["quantity"],
                        product=arguments["product"],
                        order_type=arguments["order_type"],
                        price=arguments.get("price"),
                        variety="regular"
                    )
                    return [TextContent(type="text", text=f"Order placed: {order_id}")]
                
                elif name == "get_holdings":
                    if not self.kite:
                        return [TextContent(type="text", text="Configure first")]
                    holdings = await asyncio.to_thread(self.kite.holdings)
                    return [TextContent(type="text", text=f"Holdings:\n```json\n{json.dumps(holdings, indent=2)}\n```")]
                
                elif name == "get_gtt_orders":
                    if not self.kite:
                        return [TextContent(type="text", text="Configure first")]
                    gtt_orders = await asyncio.to_thread(self.kite.gtts)
                    return [TextContent(type="text", text=f"GTT Orders:\n```json\n{json.dumps(gtt_orders, indent=2, default=str)}\n```")]
                
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

async def main():
    server = KiteMCPServer()
    async with AsyncExitStack() as stack:
        streams = await stack.enter_async_context(stdio_server())
        await server.server.run(
            streams[0], streams[1],
            InitializationOptions(
                server_name="kite-mcp-server",
                server_version="1.0.0",
                capabilities=ServerCapabilities()
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
