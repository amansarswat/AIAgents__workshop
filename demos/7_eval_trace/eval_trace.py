"""
DEMO 7 — EVAL & TRACE: the part of agent work that actually pays the bills
==========================================================================
Anyone can get one happy-path run to look good on stage. Shipping an agent means
answering: *how often is it right, how much does it cost, how slow is it, and did
my last prompt change make it better or worse?* You cannot answer that by eyeballing
output. You need a TRACE (what happened, step by step, with tokens + latency) and an
EVAL (a score against known-good answers).

This is a minimal but real harness:
  • AGENT UNDER TEST — a support-ticket triage agent: ticket text -> {category,
    priority, justification} as structured JSON.
  • TRACE — every run records latency, prompt/completion tokens, the raw model output,
    and the outcome. (In prod this is your span/observability data.)
  • EVAL — two complementary scorers:
       1. deterministic check: predicted category == gold label (exact, free, 100% reliable).
       2. LLM-as-judge: a second model rates the justification 1–5 against a rubric
          (catches quality a string match can't — but costs tokens and can be wrong,
          so you anchor it with the deterministic check).
  • SCORECARD — accuracy, avg judge score, p50/p95 latency, tokens, $ cost across the set.

Run:  python demos/7_eval_trace/eval_trace.py     (needs your Azure .env)
"""

import os
import sys
import json
import time
from pathlib import Path
from dataclasses import dataclass

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from openai import AzureOpenAI

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")

# Illustrative gpt-4o-mini pricing (USD/token). Adjust to your Azure rates.
PRICE_IN, PRICE_OUT = 0.15 / 1_000_000, 0.60 / 1_000_000

CATEGORIES = ["billing", "bug", "feature_request", "account", "other"]
PRIORITIES = ["low", "medium", "high", "urgent"]

# The eval set: input + the GOLD category we expect. This is the asset that makes
# iteration possible — change the prompt, re-run, compare the scorecard.
GOLD = [
    {"ticket": "I was charged twice for my Orbit subscription this month — please refund the duplicate.", "category": "billing"},
    {"ticket": "The 'export orders' button in the Orbit dashboard throws a 500 error every time I click it.", "category": "bug"},
    {"ticket": "It would be great if the Orbit seller dashboard had a dark mode.", "category": "feature_request"},
    {"ticket": "I can't log into my Orbit account — it says locked after I changed my email.", "category": "account"},
    {"ticket": "URGENT: our Orbit storefront checkout returns 503 for every shopper in production!", "category": "bug"},
]

SYS = (
    "You are a support-ticket triage system. Classify the ticket and respond with ONLY a JSON "
    "object: {\"category\": one of " + str(CATEGORIES) + ", \"priority\": one of " + str(PRIORITIES) +
    ", \"justification\": a one-sentence reason}. No prose, no markdown."
)


@dataclass
class Trace:
    case: int
    ticket: str
    gold: str
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: str = ""
    category: str = ""
    priority: str = ""
    justification: str = ""
    correct: bool = False
    judge_score: int = 0
    error: str = ""


def run_agent(ticket: str) -> tuple[str, object, float]:
    """One classification call. Returns (raw_text, usage, latency_ms)."""
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "system", "content": SYS}, {"role": "user", "content": ticket}],
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=120,
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    return resp.choices[0].message.content or "", resp.usage, latency_ms


def judge(ticket: str, justification: str) -> int:
    """LLM-as-judge: rate the justification 1–5. Anchored by a tight rubric."""
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You grade a support-triage justification 1-5 "
             "(5 = specific and clearly correct for the ticket, 1 = vague/wrong). "
             "Reply with ONLY the integer."},
            {"role": "user", "content": f"Ticket: {ticket}\nJustification: {justification}\nScore (1-5):"},
        ],
        temperature=0,
        max_tokens=3,
    )
    raw = (resp.choices[0].message.content or "").strip()
    digits = "".join(c for c in raw if c.isdigit())
    return max(1, min(5, int(digits))) if digits else 1


def evaluate(gold_set) -> list:
    traces = []
    for i, item in enumerate(gold_set, start=1):
        tr = Trace(case=i, ticket=item["ticket"], gold=item["category"])
        try:
            raw, usage, latency_ms = run_agent(item["ticket"])
            tr.raw, tr.latency_ms = raw, latency_ms
            tr.prompt_tokens, tr.completion_tokens = usage.prompt_tokens, usage.completion_tokens
            parsed = json.loads(raw)
            tr.category = str(parsed.get("category", "")).strip().lower()
            tr.priority = str(parsed.get("priority", "")).strip().lower()
            tr.justification = str(parsed.get("justification", "")).strip()
            tr.correct = tr.category == tr.gold
            tr.judge_score = judge(tr.ticket, tr.justification)
        except Exception as e:
            tr.error = repr(e)
        traces.append(tr)
        mark = "✓" if tr.correct else "✗"
        print(f"  case {i}: pred={tr.category or '—':<15} gold={tr.gold:<15} {mark}  "
              f"judge={tr.judge_score}/5  {tr.latency_ms:6.0f}ms" + (f"  ERROR {tr.error}" if tr.error else ""))
    return traces


def show_trace(tr: Trace) -> None:
    print("\n" + "─" * 70)
    print(f"FULL TRACE — case {tr.case} (this is what your observability layer would capture)")
    print("─" * 70)
    print(f"  step 1  classify   model={DEPLOYMENT}  latency={tr.latency_ms:.0f}ms  "
          f"tokens={tr.prompt_tokens}+{tr.completion_tokens}")
    print(f"          input    : {tr.ticket}")
    print(f"          raw out  : {tr.raw}")
    print(f"  step 2  check      predicted '{tr.category}' vs gold '{tr.gold}'  ->  "
          f"{'PASS' if tr.correct else 'FAIL'}")
    print(f"  step 3  judge      justification scored {tr.judge_score}/5")


def scorecard(traces: list) -> None:
    n = len(traces)
    ok = [t for t in traces if not t.error]
    acc = sum(t.correct for t in ok) / n if n else 0
    avg_judge = sum(t.judge_score for t in ok) / len(ok) if ok else 0
    lat = sorted(t.latency_ms for t in ok)
    p50 = lat[len(lat) // 2] if lat else 0
    p95 = lat[max(0, int(len(lat) * 0.95) - 1)] if lat else 0
    in_tok = sum(t.prompt_tokens for t in traces)
    out_tok = sum(t.completion_tokens for t in traces)
    cost = in_tok * PRICE_IN + out_tok * PRICE_OUT

    print("\n" + "=" * 70)
    print("SCORECARD  (this is the artifact you diff across prompt/model changes)")
    print("=" * 70)
    print(f"  cases                : {n}")
    print(f"  category accuracy    : {acc:.0%}  ({sum(t.correct for t in ok)}/{n})")
    print(f"  avg judge score      : {avg_judge:.2f} / 5")
    print(f"  latency p50 / p95    : {p50:.0f}ms / {p95:.0f}ms")
    print(f"  tokens (in+out)      : {in_tok}+{out_tok}")
    print(f"  eval cost            : ${cost:.6f}")
    if any(t.error for t in traces):
        print(f"  errors               : {sum(1 for t in traces if t.error)} (see trace above)")
    print("\nTakeaway: this scorecard — not a single happy-path run — is how you know")
    print("whether your last change helped. Wire the trace into real observability and")
    print("run the eval in CI on every prompt/model bump.")


if __name__ == "__main__":
    gold_set = list(GOLD)
    extra = os.getenv("DEMO_EVAL_TICKET", "").strip()
    if extra:
        gold_set.append({"ticket": extra, "category": (os.getenv("DEMO_EVAL_EXPECT", "other").strip().lower() or "other")})

    print(f"Model deployment: {DEPLOYMENT}")
    print(f"Evaluating {len(gold_set)} tickets…\n")
    traces = evaluate(gold_set)
    show_trace(traces[0])
    scorecard(traces)
