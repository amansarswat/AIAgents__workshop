# Demo 4 (finale) — Model Context Protocol: connect an agent to your own tools

**Agent type:** agent + standardized, reusable tool servers (MCP).
**Source:** `ed-donner/agents` → `6_mcp` (lab 2), simplified to need no paid APIs.

## Why MCP matters
Every framework so far hand-codes tools *into* the agent. MCP flips it: you publish
tools **once** as a server, and **any** MCP-aware client (our agent, Claude Desktop,
Cursor, VS Code…) can use them. It's "USB-C for AI tools" — and it's where the
industry is standardizing.

## What it shows live
```
mcp_agent.py  ──launches──►  accounts_server.py (your MCP server, a subprocess)
     │                              │  exposes: get_balance, get_holdings,
     │  auto-discovers tools ◄──────┘           buy_shares, sell_shares
     └─► Azure agent uses them to trade for "Alice", reports balance + holdings
```
The headline: **`mcp_agent.py` contains no trading logic at all.** It points at a
server, the tools appear, the agent uses them.

## Files
- `accounts.py` — a tiny self-contained account model (fixed prices, local JSON).
- `accounts_server.py` — **the MCP server you wrote**: `@mcp.tool()` on plain functions.
- `mcp_agent.py` — an OpenAI Agents SDK agent that connects to the server over stdio.

## Run
```bash
python demos/4_mcp_trading/mcp_agent.py
```
First it prints the discovered tool names, then the agent buys shares and reports back.
State persists in `accounts.json` (delete it to reset Alice's account).

## Azure notes
Same Azure wiring as Demo 2 (`AsyncAzureOpenAI` → `OpenAIChatCompletionsModel`,
tracing disabled). The agent launches the server with `sys.executable` so it uses
the same Python/venv on any OS.

## Application
Internal "tool platforms": expose your CRM, database, or trading system as one MCP
server and let every agent/team connect to it without re-implementing the glue.
