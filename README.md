# ZerodhaMCP
This project implements a minimal **Model Context Protocol (MCP) server** for **Zerodha Kite Connect**, allowing programmatic access to trading resources and operations. It provides a structured interface for retrieving account data, monitoring positions, and executing trades directly via MCP.  

## Features  
- **Resource Access**  
  - User Profile  
  - Portfolio Holdings  
  - Trading Positions  
  - Order Book  
  - Account Funds  
  - Active GTT (Good Till Triggered) Orders  

- **Trading Tools**  
  - Configure Kite Connect with API key and access token  
  - Fetch real-time market quotes  
  - Place new buy/sell orders  
  - Modify existing orders  
  - Cancel orders  
  - Retrieve holdings and GTT orders  

- **Server Integration**  
  - Uses `asyncio` for non-blocking execution  
  - Provides structured logs for actions and errors  
  - Exposes resources and tools in a standardized MCP format  

## Example Workflow  
1. **Configure Kite Connect** with your `api_key` and `access_token`.  
2. **Fetch Resources** such as profile, portfolio, or funds.  
3. **Get Quotes** for live instruments.  
4. **Place Orders** (buy/sell) with parameters like symbol, exchange, quantity, and order type.  
5. **Modify or Cancel Orders** as needed.  
6. **View Active GTT Orders** to track conditional trades.  

