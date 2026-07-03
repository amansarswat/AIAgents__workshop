# Demo 5 — Native & Hybrid Agents (agentic ≠ AI-dependent)

**Agent type:** deterministic ("native") agents, and native-first **hybrid** agents.
**The point:** *the agent loop is the same shape whether the brain is an LLM or
plain code.* Native decisions cost **$0** and are instant + testable. Use the LLM
only when the decision is genuinely open-ended — that's how you keep cost in check.

This is the cost-control counterpoint to Demo 1: show it right after the LLM loop.

## 5a — `native_agent.py` (no LLM, no key, $0.00)
A real autonomous remediation agent (perceive → decide → act → observe → repeat)
whose **brain is a rule-based policy** — zero tokens. It nurses an unhealthy server
back to health:
```
START: cpu=95% mem=88% disk=93% errors=7.0% service=DOWN
turn 1: restart_service  -> service UP, mem 35%
turn 2: clear_logs       -> disk 45%
turn 3: scale_out        -> cpu 45%
turn 4: HEALTHY — done        LLM calls: 0 • Tokens: 0 • Cost: $0.00
```
```bash
python demos/5_native_agents/native_agent.py     # no .env needed
```

## 5b — `hybrid_agent.py` (native-first, escalate only when stuck — with a cost meter)
Triages a batch of incidents. Known alert types hit a free **rule playbook**; only
the novel ones escalate to Azure. A live meter shows the savings:
```
[RULE  $0.00] disk_full -> clear_logs        ... (10 of these)
[LLM   ~paid] unknown   -> rollback_deploy   (103+4 tok)   ... (2 of these)
COST METER: 10/12 free (83%), 2 escalated → ~83% fewer LLM calls
```
```bash
python demos/5_native_agents/hybrid_agent.py     # needs your Azure .env
```

## Why this matters
| | Native (rules) | LLM | Hybrid |
|---|---|---|---|
| Cost / decision | **$0** | tokens ≈ ¢ | mostly $0, ¢ for the hard ones |
| Latency | µs | network round-trip | mixed |
| Predictable / testable | ✅ fully | ❌ stochastic | ✅ for the rule path |
| Handles novel cases | ❌ | ✅ | ✅ (escalates) |

**Rule of thumb:** don't pay a model to make a decision a rule already knows.
Most production "agents" are mostly deterministic, with a little LLM at the edges.

## Application
Auto-remediation / SRE runbooks, alert triage, ETL guards, form/RPA bots, routing
layers — anywhere the common path is well-understood and only the long tail is fuzzy.
This is also exactly the design an **agentic_devops** platform wants: cheap rules for
the 90%, model reasoning for the surprises.
