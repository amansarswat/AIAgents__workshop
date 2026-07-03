"""
DEMO 9 — LangGraph: a stateful agent with retry-until-criteria + a human gate
=============================================================================
The earlier framework demos run a flow once and hope. Real workflows are graphs you
can SEE and CONTROL: explicit nodes, conditional edges, cycles, persisted state, and
the ability to PAUSE for a human before doing something consequential. That is exactly
what LangGraph is for, and it's the framework a senior reaches for when "an agent that
calls some tools" isn't enough.

This graph implements two production-grade patterns at once:

  1. EVALUATOR–OPTIMIZER (retry-until-criteria):
         generate ─► evaluate ─► (score < bar AND iters < max?) ─► back to generate
                                  └────────── else ──────────────► human gate
     The draft is regenerated WITH the judge's feedback until it clears a quality bar
     (or hits a max-iteration cap so it can never loop forever).

  2. HUMAN-IN-THE-LOOP approval gate:
     Before the consequential "publish" step, the graph hits `interrupt()` and PAUSES.
     Its state is checkpointed. A human inspects the proposal and resumes with a
     decision; only "approve" lets `publish` run. (Driven here by DEMO_APPROVE so the
     script is non-interactive, but the pause/resume is LangGraph's real mechanism —
     in prod the human could approve hours later from a different process.)

Run:  python demos/9_langgraph_workflow/langgraph_workflow.py     (needs your Azure .env)
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import TypedDict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
_common = dict(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    azure_deployment=DEPLOYMENT,
)
llm_gen = AzureChatOpenAI(temperature=0.5, **_common)
llm_judge = AzureChatOpenAI(temperature=0, **_common)

QUALITY_BAR = int(os.getenv("DEMO_BAR", "4"))     # require judge score >= this (1–5)
MAX_ITERS = int(os.getenv("DEMO_MAX_ITERS", "3"))  # hard cap so the cycle can't run forever


# =====================================================================
# STATE — the typed object that flows through (and is checkpointed in) the graph.
# =====================================================================
class State(TypedDict):
    task: str
    draft: str
    score: int
    feedback: str
    iterations: int
    approved: bool
    final: str


# =====================================================================
# NODES
# =====================================================================
def generate(state: State) -> dict:
    n = state.get("iterations", 0) + 1
    fb = state.get("feedback", "")
    msgs = [SystemMessage(content="You are a crisp marketing copywriter. Return ONLY the copy, no preamble.")]
    if fb:
        msgs.append(HumanMessage(content=f"Task: {state['task']}\n\nYour previous draft:\n{state['draft']}\n\n"
                                         f"Revise it to fix this feedback:\n{fb}"))
    else:
        msgs.append(HumanMessage(content=state["task"]))
    draft = llm_gen.invoke(msgs).content.strip()
    print(f"\n[generate · iter {n}] {draft}")
    return {"draft": draft, "iterations": n}


def evaluate(state: State) -> dict:
    rubric = ("Score the copy 1-5 against: (a) specific (names the product/benefit), "
              "(b) <= 200 characters, (c) no empty hype words ('revolutionary', 'game-changing'). "
              "Respond ONLY as JSON: {\"score\": int, \"feedback\": \"what to fix\"}.")
    out = llm_judge.invoke([SystemMessage(content=rubric),
                            HumanMessage(content=f"Task: {state['task']}\nCopy: {state['draft']}")]).content
    try:
        parsed = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
        score, feedback = int(parsed.get("score", 1)), str(parsed.get("feedback", "")).strip()
    except Exception:
        score, feedback = 1, "could not parse judge output"
    score = max(1, min(5, score))
    print(f"[evaluate] score={score}/5  ·  feedback: {feedback}")
    return {"score": score, "feedback": feedback}


def route_after_eval(state: State) -> str:
    if state["score"] >= QUALITY_BAR:
        print(f"  → meets bar ({state['score']} >= {QUALITY_BAR}); proceed to human gate")
        return "gate"
    if state["iterations"] >= MAX_ITERS:
        print(f"  → hit max iterations ({MAX_ITERS}); proceed with best effort")
        return "gate"
    print(f"  → below bar ({state['score']} < {QUALITY_BAR}); revise")
    return "generate"


def gate(state: State) -> dict:
    # The graph PAUSES here. State is checkpointed; a human decides; we resume.
    decision = interrupt({"proposal": state["draft"], "score": state["score"],
                          "ask": "approve to publish? (approve/reject)"})
    approved = str(decision).strip().lower() == "approve"
    print(f"\n[gate] human decision: {decision!r} → {'APPROVED' if approved else 'REJECTED'}")
    return {"approved": approved}


def route_after_gate(state: State) -> str:
    return "publish" if state.get("approved") else "rejected"


def publish(state: State) -> dict:
    print("[publish] ✅ consequential action executed (e.g. posted to the blog / sent).")
    return {"final": f"PUBLISHED: {state['draft']}"}


def rejected(state: State) -> dict:
    print("[rejected] human declined; nothing was published.")
    return {"final": "NOT PUBLISHED — rejected at the human gate."}


def build_graph():
    g = StateGraph(State)
    g.add_node("generate", generate)
    g.add_node("evaluate", evaluate)
    g.add_node("gate", gate)
    g.add_node("publish", publish)
    g.add_node("rejected", rejected)
    g.add_edge(START, "generate")
    g.add_edge("generate", "evaluate")
    g.add_conditional_edges("evaluate", route_after_eval, {"generate": "generate", "gate": "gate"})
    g.add_conditional_edges("gate", route_after_gate, {"publish": "publish", "rejected": "rejected"})
    g.add_edge("publish", END)
    g.add_edge("rejected", END)
    # A checkpointer is what makes pause/resume (and durable state) possible.
    return g.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    task = os.getenv("DEMO_TASK") or (
        "Write a one-sentence launch announcement (max 200 characters) for Orbit's new "
        "one-click checkout. Be specific; avoid hype words."
    )
    decision = (os.getenv("DEMO_APPROVE") or "approve").strip().lower()

    print(f"Model deployment: {DEPLOYMENT}")
    print(f"TASK: {task}")
    print(f"Quality bar: score >= {QUALITY_BAR}/5  ·  max revisions: {MAX_ITERS}  ·  human decision: {decision!r}")

    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-9"}}

    # Run until the graph pauses at the human gate.
    result = graph.invoke({"task": task, "draft": "", "feedback": "", "iterations": 0}, config)

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("\n" + "─" * 70)
        print("⏸  GRAPH PAUSED at human gate (state checkpointed). Awaiting decision.")
        print(f"   proposal : {payload['proposal']}")
        print(f"   quality  : {payload['score']}/5")
        print("─" * 70)
        # Resume with the human's decision — could happen in a totally separate process.
        result = graph.invoke(Command(resume=decision), config)

    print("\n" + "=" * 70)
    print("OUTCOME")
    print("=" * 70)
    print(result.get("final", "(no final state)"))
    print(f"(took {result.get('iterations', '?')} generation(s) to clear the bar)")
