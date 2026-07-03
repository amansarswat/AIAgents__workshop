"""
DEMO 12 — MODEL ROUTER (LiteLLM): cheap model for easy work, frontier only when it's worth it
=============================================================================================
Sending every request to a frontier model is the second-most-common way an LLM bill
explodes (the first is the loop from Demo 10). Most traffic is easy — a lookup, a
reformat, a one-line summary — and a small, cheap model nails it. You only need the
expensive model for genuine multi-step reasoning.

This demo routes each task to a MODEL TIER, through **LiteLLM** — one provider-agnostic
call API (`litellm.completion(model="azure/<deployment>", ...)`) that can front Azure,
OpenAI, Anthropic, Bedrock, local models, etc. Swapping the model is a string change.

  • a CHEAP model classifies each task SIMPLE vs COMPLEX  (a few tokens),
  • SIMPLE  -> cheap model  (gpt-4o-mini),
  • COMPLEX -> frontier model (gpt-4o / gpt-4.1),
  • a cost meter compares this cascade against "frontier-for-everything".

This complements Demo 1b (rules vs LLM). There the choice was *code vs model*; here it's
*cheap model vs expensive model* — the same "use the least capable thing that works" idea,
one tier up.

Config: CHEAP = AZURE_OPENAI_CHAT_DEPLOYMENT. FRONTIER = AZURE_OPENAI_FRONTIER_DEPLOYMENT
(set it to a real frontier deployment, e.g. `gpt-4o`, to see true multi-model routing). If
it isn't set, both tiers use your one deployment so the demo still runs, and costs are shown
at each tier's LIST price to illustrate the saving.

Run:  python demos/12_model_router/model_router.py     (needs your Azure .env)
"""

import os
import sys
import logging
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
import litellm

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# LiteLLM reads Azure creds from these names — translate from our AZURE_OPENAI_* vars.
os.environ["AZURE_API_KEY"] = os.environ["AZURE_OPENAI_API_KEY"]
os.environ["AZURE_API_BASE"] = os.environ["AZURE_OPENAI_ENDPOINT"]
os.environ["AZURE_API_VERSION"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

CHEAP = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
FRONTIER = os.getenv("AZURE_OPENAI_FRONTIER_DEPLOYMENT", CHEAP)
FRONTIER_IS_REAL = FRONTIER != CHEAP

# List prices (USD per token): gpt-4o-mini vs a gpt-4o-class frontier model.
PRICE = {"cheap": (0.15 / 1e6, 0.60 / 1e6), "frontier": (2.50 / 1e6, 10.0 / 1e6)}


def call(deployment: str, messages: list, max_tokens: int = 400):
    """One LiteLLM call to an Azure deployment. Returns (text, prompt_tok, completion_tok)."""
    r = litellm.completion(model=f"azure/{deployment}", messages=messages,
                           temperature=0, max_tokens=max_tokens)
    u = r.usage
    return (r.choices[0].message.content or "").strip(), u.prompt_tokens, u.completion_tokens


def classify(task: str):
    """Cheap-model router: SIMPLE vs COMPLEX. Returns (tier, prompt_tok, completion_tok)."""
    text, pt, ct = call(CHEAP, [
        {"role": "system", "content":
            "You route tasks to a model tier. Reply with EXACTLY one word: SIMPLE or COMPLEX.\n"
            "SIMPLE  = a fact lookup, a reformat, a definition, or a one-line summary (answerable in a sentence).\n"
            "COMPLEX = multi-step reasoning, system design, planning, trade-off analysis, or math with steps.\n"
            "Examples:\n"
            "'What is the capital of France?' -> SIMPLE\n"
            "'Reformat this date to DD/MM/YYYY' -> SIMPLE\n"
            "'Design a caching layer and discuss eviction/consistency trade-offs' -> COMPLEX\n"
            "'Give a zero-downtime plan to split a database table' -> COMPLEX"},
        {"role": "user", "content": f"Task: {task}\nOne word:"},
    ], max_tokens=4)
    return ("frontier" if "COMPLEX" in text.upper() else "cheap"), pt, ct


# Orbit's incoming AI request stream — mostly routine (cheap), a few need real reasoning (frontier).
TASKS = [
    "Reformat this Orbit order date 2026-07-02 to DD/MM/YYYY.",
    "What does HTTP status 404 mean when Orbit's API returns it?",
    "Give the plural of 'analysis' for the Orbit help docs.",
    "Translate the Orbit greeting 'good morning' into Spanish.",
    "Summarize in one line: 'Orbit's status meeting moved from Tuesday to Thursday at 3pm.'",
    "Write a one-line order-confirmation blurb for an Orbit customer who bought 2 items.",
    "Design a retry-and-backoff strategy for Orbit's checkout calling three flaky payment "
    "gateways; cover failure classification, idempotency, and when to fail over vs escalate.",
    "Propose a zero-downtime plan to split Orbit's monolithic 'users' table into 'users' and "
    "'profiles'. List the ordered migration steps and the rollback for each.",
]


def cost(tier: str, pt: int, ct: int) -> float:
    pin, pout = PRICE[tier]
    return pt * pin + ct * pout


def main():
    extra = os.getenv("DEMO_EXTRA_TASK", "").strip()
    tasks = TASKS + ([extra] if extra else [])

    print(f"CHEAP tier    : azure/{CHEAP}")
    print(f"FRONTIER tier : azure/{FRONTIER}" + ("" if FRONTIER_IS_REAL else "   (not configured → using the cheap "
          "deployment; costs shown at frontier LIST price to illustrate)"))
    print(f"\nRouting {len(tasks)} tasks through LiteLLM…\n")

    router_cost = 0.0
    cheap_actual = cheap_at_frontier = 0.0   # tasks routed to the cheap model
    frontier_actual = 0.0                    # tasks routed to the frontier model
    all_frontier = 0.0                       # every task, if sent straight to frontier
    n_cheap = n_frontier = 0

    for task in tasks:
        tier, r_pt, r_ct = classify(task)
        router_cost += cost("cheap", r_pt, r_ct)  # the router itself runs on the cheap model
        deployment = FRONTIER if tier == "frontier" else CHEAP
        answer, pt, ct = call(deployment, [{"role": "user", "content": task}], max_tokens=350)
        all_frontier += cost("frontier", pt, ct)
        if tier == "cheap":
            n_cheap += 1
            cheap_actual += cost("cheap", pt, ct)
            cheap_at_frontier += cost("frontier", pt, ct)
            tag = "CHEAP   "
        else:
            n_frontier += 1
            frontier_actual += cost("frontier", pt, ct)
            tag = "FRONTIER"
        print(f"[→ {tag}] {task[:56]:<56}  ({pt}+{ct} tok)")
        print(f"             ans: {' '.join(answer.split())[:88]}")

    total = len(tasks)
    cascade = router_cost + cheap_actual + frontier_actual
    mult = (cheap_at_frontier / cheap_actual) if cheap_actual else 0
    print("\n" + "=" * 70)
    print("COST METER  (LiteLLM — one API, any model behind a string)")
    print("=" * 70)
    print(f"  tasks                          : {total}   →   {n_cheap} cheap, {n_frontier} frontier")
    print(f"  routed-cheap tasks cost        : ${cheap_actual:.6f}")
    print(f"    the same tasks on frontier   : ${cheap_at_frontier:.6f}   ({mult:.0f}× more for identical work)")
    print(f"  routed-frontier tasks cost     : ${frontier_actual:.6f}   (these genuinely needed the big model)")
    print(f"  router overhead                : ${router_cost:.6f}")
    print(f"  — total this run (cascade)     : ${cascade:.6f}")
    print(f"  — frontier-for-everything      : ${all_frontier:.6f}")
    if all_frontier:
        print(f"  saving vs all-frontier         : {(1 - cascade / all_frontier):.0%}")
    print(f"\nThe headline is the {mult:.0f}× multiplier: every routine request answered by the cheap model")
    print("costs a fraction of the frontier price — and at real volumes, routine requests dominate.")
    print("LiteLLM makes the model a config value; the same code calls OpenAI, Anthropic, Bedrock or a")
    print("local model by changing `azure/<deployment>` to another string.")
    if not FRONTIER_IS_REAL:
        print("Set AZURE_OPENAI_FRONTIER_DEPLOYMENT=gpt-4o to route the hard tasks to a real frontier model.")


if __name__ == "__main__":
    main()
