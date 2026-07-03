"""
DEMO 5b — HYBRID AGENTS: native-first, escalate to the LLM only when stuck
==========================================================================
The cost lesson, made concrete.

In the real world ~90% of incidents are well-understood and map to a known
playbook — those should be handled by FREE, instant native rules. Only the rare,
novel, ambiguous incident needs an LLM to reason about it.

This agent triages a batch of incidents:
  • If the alert matches a rule  -> native decision   (0 tokens, $0.00)
  • If it doesn't                -> escalate to Azure (a few tokens, a few ¢)

A live cost meter tallies how many decisions were free vs. paid, so you can see
exactly how much an "LLM-for-everything" design would have wasted.

Run:  python demos/5_native_agents/hybrid_agent.py     (needs your Azure .env)
"""

import os
import sys
from pathlib import Path

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

# Illustrative gpt-4o-mini pricing (USD per token). Adjust to your Azure rates.
PRICE_IN = 0.15 / 1_000_000
PRICE_OUT = 0.60 / 1_000_000

ACTIONS = [
    "restart_service", "clear_logs", "scale_out", "rollback_deploy",
    "block_ip", "rotate_credentials", "page_human", "ignore",
]

# The native "brain": a playbook mapping known alert types to actions. Free + instant.
RULES = {
    "service_down": "restart_service",
    "disk_full": "clear_logs",
    "high_cpu": "scale_out",
    "high_error_rate": "rollback_deploy",
    "memory_leak": "restart_service",
    "ddos_from_ip": "block_ip",
    "cert_expiring": "rotate_credentials",
    "healthcheck_flap": "ignore",
}

# A realistic incoming stream: mostly known, a couple genuinely novel.
INCIDENTS = [
    ("disk_full", "/var/log at 96% on web-03"),
    ("high_cpu", "api-01 CPU pinned at 99% for 10m"),
    ("service_down", "payments-svc not responding to healthcheck"),
    ("cert_expiring", "TLS cert for api.example.com expires in 36h"),
    ("high_error_rate", "checkout 500s at 8% after 14:02 deploy"),
    ("ddos_from_ip", "120k req/s from 203.0.113.7"),
    ("memory_leak", "worker-02 RSS climbing, now 88%"),
    ("disk_full", "/data at 94% on db-replica-2"),
    ("healthcheck_flap", "lb healthcheck flapped twice, now stable"),
    ("high_cpu", "batch-runner CPU 91% during nightly job"),
    # --- the two that no rule covers: the LLM earns its keep here ---
    ("unknown", "Intermittent 502s ONLY on EU edge nodes since the 14:02 config "
                "push; CPU/mem/disk all normal; US edge unaffected."),
    ("unknown", "Latency p99 tripled right after enabling the new cache layer, "
                "but error rate and resource usage are flat."),
]

# (UI) Optionally append your own incident so you can watch the LLM escalation path on
# a case you invented. Empty by default → identical to a standalone run.
_extra = os.getenv("DEMO_EXTRA_INCIDENT", "").strip()
if _extra:
    INCIDENTS.append(("unknown", _extra))


def decide_with_llm(alert_type: str, description: str):
    """Escalation path: ask the model to pick ONE action. Returns (action, tokens)."""
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You are an on-call SRE. Choose exactly ONE "
             "action for the incident. Reply with only the action keyword, nothing else. "
             "Allowed actions: " + ", ".join(ACTIONS)},
            {"role": "user", "content": f"Alert type: {alert_type}\nDetails: {description}"},
        ],
        max_tokens=12,
        temperature=0,
    )
    raw = (resp.choices[0].message.content or "").strip().lower()
    action = next((a for a in ACTIONS if a in raw), "page_human")
    u = resp.usage
    tokens = (u.prompt_tokens, u.completion_tokens)
    return action, tokens


def main():
    print(f"Model deployment (escalation only): {DEPLOYMENT}\n")
    by_rule = by_llm = 0
    in_tok = out_tok = 0

    for atype, desc in INCIDENTS:
        if atype in RULES:
            action = RULES[atype]
            by_rule += 1
            print(f"[RULE  $0.00] {atype:<16} -> {action}")
        else:
            action, (pt, ct) = decide_with_llm(atype, desc)
            by_llm += 1
            in_tok += pt
            out_tok += ct
            print(f"[LLM   ~paid] {atype:<16} -> {action}   ({pt}+{ct} tok)")

    total = len(INCIDENTS)
    actual_cost = in_tok * PRICE_IN + out_tok * PRICE_OUT
    # Project what an "LLM-for-everything" design would have cost.
    avg_per_llm = (actual_cost / by_llm) if by_llm else 0.0
    all_llm_cost = avg_per_llm * total

    print("\n" + "=" * 70)
    print("COST METER")
    print("=" * 70)
    print(f"Incidents handled        : {total}")
    print(f"  by native rules ($0)   : {by_rule}  ({by_rule / total:.0%})")
    print(f"  escalated to the LLM   : {by_llm}  ({by_llm / total:.0%})")
    print(f"LLM tokens used          : {in_tok} in + {out_tok} out")
    print(f"Actual decision cost     : ${actual_cost:.6f}")
    print(f"If EVERY decision used the LLM (projected): ${all_llm_cost:.6f}")
    if all_llm_cost:
        print(f"Savings from native-first routing        : "
              f"{(1 - actual_cost / all_llm_cost):.0%} "
              f"({by_rule} of {total} decisions made for free)")
    print("\nTakeaway: don't pay a model to make a decision a rule already knows.")


if __name__ == "__main__":
    main()
