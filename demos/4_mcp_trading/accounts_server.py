"""
An MCP SERVER you wrote yourself.

Model Context Protocol (MCP) is a standard way to expose tools & data to ANY
agent. FastMCP turns ordinary Python functions into MCP tools with one decorator.
This server speaks over stdio: the agent launches it as a subprocess and talks to
it on stdin/stdout. The same server could plug into Claude Desktop, Cursor, or any
MCP-aware client — not just our demo.

Run on its own (it will just wait for an MCP client to connect):
    python demos/4_mcp_trading/accounts_server.py
Normally you don't run it directly — mcp_agent.py launches it for you.
"""

from mcp.server.fastmcp import FastMCP
from accounts import Account

mcp = FastMCP("accounts_server")


@mcp.tool()
async def get_store_credit(name: str) -> float:
    """Get the store-credit balance of the given Orbit customer."""
    return Account.get(name).balance


@mcp.tool()
async def get_items(name: str) -> dict[str, int]:
    """Get the products (SKU -> quantity) the given Orbit customer owns."""
    return Account.get(name).holdings


@mcp.tool()
async def purchase(name: str, sku: str, quantity: int, rationale: str) -> str:
    """Purchase a product for an Orbit customer using their store credit.

    Args:
        name: The customer's name.
        sku: The product SKU, e.g. WIDGET.
        quantity: How many units to buy.
        rationale: Why this purchase makes sense.
    """
    return Account.get(name).buy_shares(sku, quantity, rationale)


@mcp.tool()
async def refund(name: str, sku: str, quantity: int, rationale: str) -> str:
    """Refund a previously purchased product back to store credit.

    Args:
        name: The customer's name.
        sku: The product SKU, e.g. WIDGET.
        quantity: How many units to refund.
        rationale: Why this refund is being issued.
    """
    return Account.get(name).sell_shares(sku, quantity, rationale)


@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    """Expose the full account report as a readable MCP resource."""
    return Account.get(name).report()


if __name__ == "__main__":
    mcp.run(transport="stdio")
