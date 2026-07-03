"""
DEMO 5a — NATIVE AGENTS: "agentic" does NOT have to mean "AI-powered"
====================================================================
The agent loop from Demo 1 is:  perceive -> decide -> act -> observe -> repeat.
Demo 1 used an LLM as the "decide" step. But the loop doesn't care what the brain
is. Here the brain is **plain deterministic Python** — a rule-based policy.

Result: a fully autonomous remediation agent that
  • makes decisions instantly (no network round-trip),
  • is 100% predictable and unit-testable,
  • and costs $0.00 — zero tokens, no API key needed.

This is the cheapest, fastest kind of agent. Reach for an LLM only when the
decision is genuinely open-ended (see hybrid_agent.py for that).

Scenario: an SRE "auto-remediation" agent that nurses an unhealthy server back to
health by reacting to its metrics — exactly the kind of work an agentic_devops
system does, but with no model behind it.

Run:  python demos/5_native_agents/native_agent.py     (no .env / no Azure needed)
"""

import os
import sys
from dataclasses import dataclass

# Keep emoji output safe on legacy Windows consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# =====================================================================
# STATE — what the agent perceives (a simulated server)
# =====================================================================
@dataclass
class Server:
    cpu: int           # %
    memory: int        # %
    disk: int          # %
    error_rate: float  # % of requests failing
    service_up: bool

    def is_healthy(self) -> bool:
        return (
            self.service_up
            and self.cpu <= 80
            and self.memory <= 85
            and self.disk <= 90
            and self.error_rate <= 5
        )

    def line(self) -> str:
        up = "UP" if self.service_up else "DOWN"
        return (f"cpu={self.cpu}%  mem={self.memory}%  disk={self.disk}%  "
                f"errors={self.error_rate}%  service={up}")


# =====================================================================
# TOOLS — the actions the agent can take (simulated effects)
# =====================================================================
def restart_service(s: Server):
    s.service_up = True
    s.memory = 35          # restart clears the leaked memory
    s.error_rate = 1.0

def clear_logs(s: Server):
    s.disk = 45

def scale_out(s: Server):
    s.cpu = 45             # load spread across more instances

def rollback_deploy(s: Server):
    s.error_rate = 0.5

def page_human(s: Server):
    pass


ACTIONS = {
    "restart_service": restart_service,
    "clear_logs": clear_logs,
    "scale_out": scale_out,
    "rollback_deploy": rollback_deploy,
    "page_human": page_human,
}


# =====================================================================
# THE BRAIN — a deterministic policy. NO LLM. This is the whole point.
# (Highest-priority problem first; one fix per turn so the loop is visible.)
# =====================================================================
def decide(s: Server) -> str:
    if not s.service_up:
        return "restart_service"
    if s.disk > 90:
        return "clear_logs"
    if s.memory > 85:
        return "restart_service"
    if s.cpu > 80:
        return "scale_out"
    if s.error_rate > 5:
        return "rollback_deploy"
    return "DONE"


# =====================================================================
# THE LOOP — identical in shape to Demo 1; only the brain changed.
# =====================================================================
def run(server: Server, max_turns: int = 10) -> None:
    print(f"START: {server.line()}\n")
    for turn in range(1, max_turns + 1):
        action = decide(server)            # <-- zero-cost decision

        if action == "DONE":
            print(f"─── turn {turn}: HEALTHY — agent is DONE ───")
            return

        print(f"─── turn {turn}: decided '{action}' ───")
        ACTIONS[action](server)            # act
        print(f"        now: {server.line()}")  # observe

    # Couldn't fix it within the budget — escalate to a human (still no LLM).
    print(f"\n─── gave up after {max_turns} turns: paging a human ───")
    page_human(server)


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "up", "on")


if __name__ == "__main__":
    # Input: the initial server state. Overridable from the UI; defaults = a sick server.
    sick = Server(
        cpu=_env_int("DEMO_CPU", 95),
        memory=_env_int("DEMO_MEM", 88),
        disk=_env_int("DEMO_DISK", 93),
        error_rate=_env_float("DEMO_ERR", 7.0),
        service_up=_env_bool("DEMO_SERVICE_UP", False),
    )
    run(sick)
    print("\n" + "=" * 70)
    print("COST REPORT")
    print("=" * 70)
    print("LLM API calls: 0   •   Tokens: 0   •   Cost: $0.00")
    print("This entire autonomous agent ran on deterministic code — no model, no key.")
