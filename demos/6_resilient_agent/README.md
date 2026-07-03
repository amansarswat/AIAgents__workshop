# Demo 6 — Resilient Agent (tools fail; recover, then escalate)

**Act 2 — Production depth.** *No API key needed — deterministic, $0.*
**Agent type:** resilience as an **engineering** concern that wraps the tool — not a model decision.

## The one idea
> You never ask an LLM "should I retry?". Retry/backoff, failover, and escalation are
> deterministic, testable code in the orchestration layer.

```
charge ──► PRIMARY ──► call_with_retry(transient? backoff+retry) ──► ✅ charged
                          │ permanent / exhausted
                          ▼
                       FALLBACK provider ──► ✅ charged
                          │ also fails
                          ▼
                       ESCALATE → durable queue (never silently dropped)
```

## What it shows live
- An **error taxonomy**: transient (503/timeout → retry with exponential backoff) vs
  permanent (402 card declined → fail fast, don't waste retries).
- **Recovery** by failing over to a secondary provider; **escalation** when all options fail.
- Fully deterministic, so the trace is reproducible and unit-testable.

## Run
```bash
python demos/6_resilient_agent/resilient_agent.py
```
Drive the scenario (also exposed in the UI):
```bash
DEMO_TRANSIENT_FAILS=5 python ...      # exceed the retry budget → failover
DEMO_PRIMARY_PERMANENT=true python ... # card declined → immediate failover
DEMO_PRIMARY_PERMANENT=true DEMO_SECONDARY_FAILS=true python ...  # both fail → escalate
```

## Talking points
- Classify errors by **type** — that single decision is the heart of resilience.
- A dropped request is the worst outcome; escalate to a queue, never fail silent.
- The model stays out of the retry loop on purpose: deterministic = testable + observable.
