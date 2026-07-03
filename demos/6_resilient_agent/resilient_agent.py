"""
DEMO 6 — RESILIENT AGENT: tools fail. Recover, then escalate.
=============================================================
Every demo so far ran the happy path. Production doesn't. Networks time out,
gateways 503, cards get declined, downstream services fall over. The senior
question is never "does it work?" — it's "what happens when the tool *fails*?"

The lesson here: **resilience is an engineering concern that wraps the tool, NOT
a decision you delegate to the model.** You do not ask an LLM "should I retry?".
You put a retry policy, a fallback, and an escalation path in the orchestration
layer — deterministic, testable, observable — and let the model decide only the
genuinely open-ended things.

This agent charges a customer through a flaky payment provider and shows the three
moves every resilient system needs:
  1. RETRY transient failures (503/timeout) with exponential backoff + jitter.
  2. Do NOT retry permanent failures (402 card_declined) — that's just burning time.
     Instead RECOVER by failing over to a secondary provider.
  3. When every option is exhausted, ESCALATE (queue for a human / safe fallback) —
     never silently drop the request.

It is deterministic (scripted outcomes, no randomness) so the trace is reproducible
and unit-testable, and it needs no API key.

Run:  python demos/6_resilient_agent/resilient_agent.py
"""

import os
import sys
import time
from dataclasses import dataclass, field

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# =====================================================================
# ERROR TAXONOMY — the single most important design choice in resilience.
# "Is this error worth retrying?" must be answered by TYPE, not by guessing.
# =====================================================================
class TransientError(Exception):
    """Temporary; the same call may succeed if retried (503, timeout, throttling)."""


class PermanentError(Exception):
    """Will never succeed on retry (402 card declined, 400 bad request). Fail fast."""


# =====================================================================
# A FLAKY TOOL — a payment provider. Outcomes are SCRIPTED for a reproducible
# demo (in the real world these are real network calls).
# =====================================================================
@dataclass
class Provider:
    name: str
    transient_fails: int = 0      # emit this many transient errors, then succeed
    permanent: bool = False       # always fail permanently (e.g. card declined)
    _calls: int = field(default=0)

    def charge(self, amount: float) -> str:
        self._calls += 1
        if self.permanent:
            raise PermanentError(f"402 card_declined from {self.name}")
        if self._calls <= self.transient_fails:
            raise TransientError(f"503 service_unavailable from {self.name} (attempt {self._calls})")
        return f"{self.name}#txn_{1000 + self._calls}"


# =====================================================================
# THE RESILIENCE LAYER — wraps the tool. Pure engineering, no model.
# =====================================================================
RETRY_POLICY = {"max_attempts": 3, "base_delay": 0.20, "factor": 2.0}


def call_with_retry(provider: Provider, amount: float) -> str:
    """Retry ONLY transient errors, with exponential backoff + jitter.
    Re-raise permanent errors immediately. Raise the last transient error if the
    attempt budget is exhausted."""
    attempts = RETRY_POLICY["max_attempts"]
    delay = RETRY_POLICY["base_delay"]
    for attempt in range(1, attempts + 1):
        try:
            txn = provider.charge(amount)
            print(f"      ✓ success on attempt {attempt}: {txn}")
            return txn
        except PermanentError as e:
            print(f"      ✗ permanent error: {e} — NOT retrying (would never succeed)")
            raise
        except TransientError as e:
            jitter = 0.03 * attempt  # deterministic 'jitter' so the trace is stable
            wait = round(delay + jitter, 3)
            if attempt == attempts:
                print(f"      ✗ transient error: {e} — retry budget exhausted ({attempts} attempts)")
                raise
            print(f"      ↻ transient error: {e} — backing off {wait}s then retrying")
            time.sleep(wait)
            delay *= RETRY_POLICY["factor"]
    raise RuntimeError("unreachable")


# =====================================================================
# THE AGENT — orchestrates recover-then-escalate. The "decide" step is a policy:
# try primary → on failure, fail over to secondary → if both fail, escalate.
# =====================================================================
def charge_customer(amount: float, primary: Provider, secondary: Provider) -> dict:
    print(f"GOAL: charge ${amount:.2f}\n")

    for label, provider in (("PRIMARY", primary), ("FALLBACK", secondary)):
        print(f"─── try {label} provider: {provider.name} ───")
        try:
            txn = call_with_retry(provider, amount)
            print(f"\n✅ CHARGED via {provider.name} ({label.lower()} path). txn={txn}")
            return {"status": "charged", "provider": provider.name, "txn": txn, "path": label.lower()}
        except (TransientError, PermanentError) as e:
            print(f"   → {label} provider unusable ({type(e).__name__}). Recovering…\n")

    # Both providers exhausted — do NOT drop the payment. Escalate to a durable queue
    # so a human / async retry worker can pick it up. Visible, never silent.
    print("─── ESCALATE: all providers exhausted ───")
    ticket = f"ESCALATION-{int(amount * 100)}"
    print(f"   queued for manual processing as {ticket}; customer told 'payment pending'")
    return {"status": "escalated", "ticket": ticket}


def _env_int(name, default):
    try:
        return int(float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_bool(name, default):
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    # Inputs (overridable from the UI). Defaults walk through all three behaviours:
    # primary recovers after 2 transient failures.
    transient = _env_int("DEMO_TRANSIENT_FAILS", 2)
    primary_permanent = _env_bool("DEMO_PRIMARY_PERMANENT", False)
    secondary_fails = _env_bool("DEMO_SECONDARY_FAILS", False)

    primary = Provider("stripe-gw", transient_fails=transient, permanent=primary_permanent)
    secondary = Provider("paypal-gw", permanent=secondary_fails)

    result = charge_customer(49.99, primary, secondary)

    print("\n" + "=" * 70)
    print("OUTCOME:", result)
    print("=" * 70)
    print("Resilience lived in CODE around the tool — retry/backoff for transient,")
    print("fail-fast + failover for permanent, escalation when exhausted. The model")
    print("was never asked 'should I retry?'. That is the senior pattern.")
