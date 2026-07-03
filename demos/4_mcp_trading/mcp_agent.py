"""
DEMO 4 (finale) — MODEL CONTEXT PROTOCOL: connect an agent to YOUR OWN tools
============================================================================
MCP is where the industry is converging: instead of hand-coding tools into every
agent, you publish tools once as an MCP server, and any agent can connect to them.

Here the OpenAI Agents SDK agent launches our `accounts_server.py` as a subprocess,
auto-discovers the tools it exposes (get_balance, buy_shares, ...), and uses them to
manage a simulated trading account — all on your Azure deployment.

The point: the agent code below knows NOTHING about accounts or trading. It just
points at an MCP server and the tools appear.

Adapted from ed-donner/agents `6_mcp/2_lab2.ipynb`, rewired for Azure OpenAI.

Run:  python demos/4_mcp_trading/mcp_agent.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Windows legacy consoles default to cp1252 and crash on emoji — force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from agents import Agent, Runner, RunHooks, OpenAIChatCompletionsModel, set_tracing_disabled
from agents.mcp import MCPServerStdio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
load_dotenv(ROOT / ".env")
set_tracing_disabled(True)

azure_client = AsyncAzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
model = OpenAIChatCompletionsModel(model=DEPLOYMENT, openai_client=azure_client)

# How to launch our MCP server: run accounts_server.py with THIS same Python,
# from this folder (so it can import accounts.py and write accounts.json here).
server_params = {
    "command": sys.executable,
    "args": ["accounts_server.py"],
    "cwd": str(HERE),
}


# Print each MCP tool call LIVE so the audience sees the agent using the discovered
# tools — not just the final answer.
class StepHooks(RunHooks):
    def __init__(self):
        self.n = 0

    async def on_tool_start(self, context, agent, tool):
        self.n += 1
        print(f"   🔧 step {self.n}: agent calls MCP tool → {getattr(tool, 'name', '?')}")

    async def on_tool_end(self, context, agent, tool, result):
        preview = " ".join(str(result).split())
        print(f"      ↩ {getattr(tool, 'name', 'tool')} returned: {preview[:160]}")


async def main():
    print(f"Model deployment: {DEPLOYMENT}\n")
    async with MCPServerStdio(params=server_params, client_session_timeout_seconds=30) as server:
        tool_names = [t.name for t in await server.list_tools()]
        print(f"🔌 Connected to MCP server. Tools discovered: {tool_names}")

        agent = Agent(
            name="account_manager",
            instructions="You manage an Orbit customer's store account (store credit + items owned) "
            "using ONLY the tools provided by the MCP server. After acting, always report the "
            "resulting store credit and items.",
            model=model,
            mcp_servers=[server],
        )

        # Input: overridable from the UI. Default request is built from the customer name.
        name = (os.getenv("DEMO_NAME") or "Alice").strip() or "Alice"
        request = os.getenv("DEMO_REQUEST") or (
            f"My name is {name}. Purchase 10 WIDGET and 2 GIZMO with my store credit, then tell "
            "me my remaining store credit and the items I own."
        )
        print("\nINPUT — request handed to the account_manager agent:")
        print(f"  {request}")
        print("\n─── live steps (each MCP tool call prints as it happens) ───")
        result = await Runner.run(agent, request, max_turns=15, hooks=StepHooks())
        print("\n=== Agent final output ===")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
