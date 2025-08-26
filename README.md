# Kite MCP Server (v3)  

This project implements a lightweight **Model Context Protocol (MCP) server** for **Zerodha Kite Connect**. It exposes trading resources and tools through MCP, enabling structured access to portfolio data, positions, orders, quotes, and trading actions.  

## Features  
- **Resource Access**  
  - Portfolio (current holdings)  
  - Positions (active positions)  
  - Orders (order book)  

- **Trading Tools**  
  - **configure** → Set API key and access token to connect Kite  
  - **quote** → Fetch real-time market quotes for instruments  
  - **place_order** → Place new buy/sell orders with custom parameters  
  - **get_holdings** → Retrieve portfolio holdings  
  - **get_gtt_orders** → Fetch active GTT (Good Till Triggered) orders  

- **Asynchronous Server**  
  - Uses `asyncio` for efficient, non-blocking operations  
  - Executes Kite API calls in background threads for responsiveness  

## Example Workflow  
1. **Configure** → Provide your `api_key` and `access_token` to establish a connection.  
2. **Fetch Resources** → Access portfolio, positions, or orders.  
3. **Get Quotes** → Retrieve live quotes for instruments.  
4. **Place Orders** → Submit buy/sell trades with required parameters.  
5. **View Holdings & GTT Orders** → Monitor investments and conditional orders.  

## Requirements  
- Python 3.9+  
- [`kiteconnect`](https://pypi.org/project/kiteconnect/) (`pip install kiteconnect`)  
- [`mcp`](https://github.com/modelcontextprotocol)  
