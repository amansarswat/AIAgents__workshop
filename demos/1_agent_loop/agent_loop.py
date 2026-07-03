"""
DEMO 1 — THE AGENT LOOP (no framework)
======================================
The single most important idea in agentic AI:

    An "agent" is just an LLM in a loop, with tools, that decides for itself
    when it is done.

There is no magic and no framework here — only the OpenAI SDK, a list of tool
definitions, and a `while` loop. Every framework you will see later (OpenAI
Agents SDK, CrewAI, LangGraph, AutoGen) is a convenience wrapper around exactly
this pattern.

Adapted from ed-donner/agents `1_foundations/5_extra.ipynb` and `app.py`,
rewired for Azure OpenAI.

Run:  python demos/1_agent_loop/agent_loop.py
"""

import os
import sys
import json
from pathlib import Path

# Windows legacy consoles default to cp1252 and crash on emoji — force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from openai import AzureOpenAI

# --- Load .env from the project root (works regardless of where you run from) ---
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# --- Wire up Azure OpenAI (this is the ONLY Azure-specific part) ---
client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")


# =====================================================================
# 1) THE TOOLS  — the agent's "hands". Plain Python functions + state.
# =====================================================================
todos: list[dict] = []  # each item: {"task": str, "done": bool, "notes": str}


def add_todos(descriptions: list[str]) -> str:
    """Add one or more steps to the plan."""
    for d in descriptions:
        todos.append({"task": d, "done": False, "notes": ""})
    return _render()


def complete_todo(index: int, notes: str) -> str:
    """Mark the 1-based step `index` as done, recording what was learned/decided."""
    if 1 <= index <= len(todos):
        todos[index - 1]["done"] = True
        todos[index - 1]["notes"] = notes
    return _render()


def _render() -> str:
    if not todos:
        return "The plan is empty."
    lines = []
    for i, t in enumerate(todos, start=1):
        box = "x" if t["done"] else " "
        line = f"  {i}. [{box}] {t['task']}"
        if t["notes"]:
            line += f"  — {t['notes']}"
        lines.append(line)
    return "PLAN:\n" + "\n".join(lines)


# Map tool name -> the function that implements it.
TOOL_FUNCS = {"add_todos": add_todos, "complete_todo": complete_todo}

# The JSON schema the LLM sees. This is how the model knows what it can call.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_todos",
            "description": "Break the user's goal into a list of concrete steps and add them to the plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The steps to add, in order.",
                    }
                },
                "required": ["descriptions"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "Mark a step complete once you have worked through it, recording your conclusion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "The 1-based step number."},
                    "notes": {"type": "string", "description": "What you decided or found for this step."},
                },
                "required": ["index", "notes"],
                "additionalProperties": False,
            },
        },
    },
]


# =====================================================================
# 2) THE LOOP — call the model; if it asks for a tool, run it and loop.
# =====================================================================
def run_agent(goal: str) -> str:
    system = (
        "You are a methodical planning agent. Given a goal, FIRST call add_todos to lay "
        "out the steps. THEN work through each step one at a time, calling complete_todo "
        "with your conclusion for that step. When every step is complete, stop calling "
        "tools and write a short final summary for the user."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": goal},
    ]

    turn = 0
    while True:  # <-- this loop IS the agent
        turn += 1
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=messages,
            tools=TOOLS,
        )
        choice = response.choices[0]

        # The model decided it is finished — no tool call requested.
        if choice.finish_reason != "tool_calls":
            print(f"\n─── LLM turn {turn}: agent is DONE ───")
            return choice.message.content

        # Otherwise: run every tool the model asked for, append results, loop again.
        print(f"\n─── LLM turn {turn}: agent requested tool(s) ───")
        messages.append(choice.message)
        for call in choice.message.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)
            print(f"   🔧 {name}({args})")
            result = TOOL_FUNCS[name](**args)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
            )


if __name__ == "__main__":
    # Input: overridable from the UI via DEMO_GOAL; default is the original goal.
    GOAL = os.getenv("DEMO_GOAL") or (
        "Plan Orbit's go-to-market launch: how a small team should take our new subscription "
        "e-commerce product to market. Work through the plan and give a recommendation."
    )
    print(f"Model deployment: {DEPLOYMENT}")
    print(f"GOAL: {GOAL}")
    final = run_agent(GOAL)
    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(final)
    print("\n" + _render())
