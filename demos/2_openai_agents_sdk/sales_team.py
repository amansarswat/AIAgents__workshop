"""
DEMO 2 — OPENAI AGENTS SDK: a multi-agent sales team
====================================================
Now we graduate from a hand-written loop to a real framework. The OpenAI Agents
SDK gives us three production ideas in ~80 lines:

  1. TOOLS              — @function_tool turns a Python function into a tool.
  2. AGENTS-AS-TOOLS    — one agent can be exposed as a tool to another agent.
  3. HANDOFFS           — an agent can hand the whole conversation to another agent.

The scenario: a Sales Manager asks three "SDR" agents (each with a different
writing style) to draft a cold email, picks the best draft, then HANDS OFF to an
Emailer agent that formats a subject line and "sends" it (stubbed to a file so the
demo needs no SendGrid account).

Adapted from ed-donner/agents `2_openai/2_lab2.ipynb`, rewired for Azure OpenAI.

Run:  python demos/2_openai_agents_sdk/sales_team.py
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
from agents import Agent, Runner, RunHooks, function_tool, OpenAIChatCompletionsModel, set_tracing_disabled

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
load_dotenv(ROOT / ".env")

# Azure can't power the SDK's hosted tracing dashboard, so turn it off.
set_tracing_disabled(True)

# Wrap an Azure client in the SDK's model object. Every Agent below uses it.
azure_client = AsyncAzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
model = OpenAIChatCompletionsModel(model=DEPLOYMENT, openai_client=azure_client)


# --- The "send email" tool. Stubbed: writes to a file instead of calling SendGrid. ---
@function_tool
def send_email(subject: str, body: str) -> dict:
    """Send the cold sales email with the given subject and body to the prospect."""
    out = HERE / "sent_email.txt"
    out.write_text(f"Subject: {subject}\n\n{body}\n", encoding="utf-8")
    print("\n📧  EMAIL SENT (saved to sent_email.txt)")
    print("─" * 70)
    print(f"Subject: {subject}\n\n{body}")
    print("─" * 70)
    return {"status": "sent", "subject": subject}


# --- Three SDR agents, each with a different style ---
sdr_professional = Agent(
    name="professional_sdr",
    instructions="You are a sales rep for Orbit, a subscription e-commerce platform that helps "
    "retailers sell online. You write professional, serious cold emails that earn a reply.",
    model=model,
)
sdr_witty = Agent(
    name="witty_sdr",
    instructions="You are a witty, engaging sales rep for Orbit (a subscription e-commerce "
    "platform for retailers). You write humorous cold emails that get a response.",
    model=model,
)
sdr_concise = Agent(
    name="concise_sdr",
    instructions="You are a busy sales rep for Orbit (subscription e-commerce SaaS). You write "
    "short, punchy cold emails that are easy to read on a phone.",
    model=model,
)

# Expose each SDR agent AS A TOOL the manager can call.
sdr_tools = [
    sdr_professional.as_tool(tool_name="professional_sdr", tool_description="Write a professional cold sales email"),
    sdr_witty.as_tool(tool_name="witty_sdr", tool_description="Write a witty cold sales email"),
    sdr_concise.as_tool(tool_name="concise_sdr", tool_description="Write a concise cold sales email"),
]

# The Emailer agent: receives the chosen draft, writes a subject, and sends it.
emailer = Agent(
    name="emailer",
    instructions="You are given the body of the single best cold email. Write a compelling "
    "subject line for it, then call the send_email tool exactly once to send it.",
    tools=[send_email],
    model=model,
    handoff_description="Formats the chosen email with a subject line and sends it.",
)

# The Sales Manager: orchestrates the SDRs, picks the winner, hands off to the Emailer.
sales_manager = Agent(
    name="sales_manager",
    instructions=(
        "You are a sales manager at Orbit. Use the three SDR tools to generate three "
        "different cold-email drafts — you never write emails yourself. Compare the drafts "
        "and pick the single best one. Then hand off to the 'emailer' agent, passing it the "
        "body of that single best email so it can be sent. Hand off exactly once."
    ),
    tools=sdr_tools,
    handoffs=[emailer],
    model=model,
)


# Print each step LIVE so the audience sees the tools, agents-as-tools and the handoff
# as they happen — not just the final email.
class StepHooks(RunHooks):
    def __init__(self):
        self.n = 0

    async def on_handoff(self, context, from_agent, to_agent):
        print(f"   🤝 HANDOFF: {from_agent.name} → {to_agent.name}  (control transfers away)")

    async def on_tool_start(self, context, agent, tool):
        self.n += 1
        print(f"   🔧 step {self.n}: '{agent.name}' calls → {getattr(tool, 'name', tool.__class__.__name__)}")

    async def on_tool_end(self, context, agent, tool, result):
        preview = " ".join(str(result).split())
        print(f"      ↩ {getattr(tool, 'name', 'tool')} returned: {preview[:140]}")


async def main():
    print(f"Model deployment: {DEPLOYMENT}")
    # Input: overridable from the UI via DEMO_TASK; default is the original brief.
    task = os.getenv("DEMO_TASK") or "Generate and send a cold sales email to the Head of E-commerce at a mid-size retailer."
    print("\nINPUT — task handed to the sales_manager agent:")
    print(f"  {task}")
    print("\nSETUP — the manager has 3 SDR agents exposed as tools (professional / witty / concise) "
          "and can hand off to the emailer (which owns the send_email tool).")
    print("\n─── live steps (each tool call & handoff prints as it happens) ───")
    result = await Runner.run(sales_manager, task, max_turns=15, hooks=StepHooks())
    print("\n=== Sales Manager final output ===")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
