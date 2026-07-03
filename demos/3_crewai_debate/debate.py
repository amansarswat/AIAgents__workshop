"""
DEMO 3 — CrewAI: a role-playing crew that debates a motion
==========================================================
A completely different paradigm from Demo 2. Instead of writing orchestration
code, in CrewAI you DECLARE a cast of agents (each with a role / goal / backstory)
and a list of tasks, and the framework runs them.

This crew has two agents and three tasks, run sequentially:
  • debater  →  task 1: argue FOR the motion
  • debater  →  task 2: argue AGAINST the motion
  • judge    →  task 3: read both arguments and decide the winner

The original course (3_crew/debate) uses YAML config files and an Anthropic judge.
Here it is one self-contained file with both agents on your Azure deployment.

Adapted from ed-donner/agents `3_crew/debate`, rewired for Azure OpenAI.

Run:  python demos/3_crewai_debate/debate.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Windows legacy consoles default to cp1252 and crash on emoji — force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# CrewAI talks to models through LiteLLM, which reads Azure creds from THESE env
# var names. We translate from the AZURE_OPENAI_* names into what LiteLLM expects.
os.environ["AZURE_API_KEY"] = os.environ["AZURE_OPENAI_API_KEY"]
os.environ["AZURE_API_BASE"] = os.environ["AZURE_OPENAI_ENDPOINT"]
os.environ["AZURE_API_VERSION"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

# CrewAI 1.x otherwise shows an interactive "view traces? [y/N]" prompt (20s hang)
# at the end of a run — disable it so the demo doesn't stall on stage.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from crewai import Agent, Task, Crew, Process, LLM  # noqa: E402

DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
# The "azure/" prefix tells LiteLLM to use Azure; the suffix is your DEPLOYMENT name.
# is_litellm=True routes through LiteLLM (reads AZURE_API_KEY/BASE/VERSION above).
# Newer CrewAI otherwise tries a "native" Azure provider needing an extra package.
azure_llm = LLM(model=f"azure/{DEPLOYMENT}", is_litellm=True)

# --- The cast: two agents. {motion} is filled in at kickoff time. ---
debater = Agent(
    role="A compelling debater",
    goal="Present a clear, convincing argument either for or against the motion: {motion}",
    backstory="You are an experienced debater known for concise, persuasive arguments.",
    llm=azure_llm,
    verbose=True,
)

judge = Agent(
    role="A fair debate judge",
    goal="Decide which side of the motion '{motion}' is more convincing, based purely on the arguments.",
    backstory="You weigh arguments on their merits alone, never your own opinions.",
    llm=azure_llm,
    verbose=True,
)

# --- The script: three tasks, run in order. Output of earlier tasks is in context. ---
propose = Task(
    description="You are PROPOSING the motion: {motion}. Make a clear, very convincing argument in favour.",
    expected_output="A concise, convincing argument in favour of the motion.",
    agent=debater,
)
oppose = Task(
    description="You are OPPOSING the motion: {motion}. Make a clear, very convincing argument against it.",
    expected_output="A concise, convincing argument against the motion.",
    agent=debater,
)
decide = Task(
    description="Review the arguments for and against the motion and decide which side is more convincing.",
    expected_output="Your verdict on which side won, and a short justification.",
    agent=judge,
)

crew = Crew(
    agents=[debater, judge],
    tasks=[propose, oppose, decide],
    process=Process.sequential,
    verbose=True,
)


if __name__ == "__main__":
    # Input: overridable from the UI via DEMO_MOTION; default is the original motion.
    motion = os.getenv("DEMO_MOTION") or "Orbit should launch a free tier to accelerate growth"
    print(f"Model deployment: azure/{DEPLOYMENT}")
    print(f"MOTION: {motion}\n")
    result = crew.kickoff(inputs={"motion": motion})
    print("\n" + "=" * 70)
    print("JUDGE'S VERDICT")
    print("=" * 70)
    print(result.raw)
