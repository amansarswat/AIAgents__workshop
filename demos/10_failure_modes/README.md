# Demo 10 — When this goes wrong in prod (failures + guards)

**Act 2 — Production depth · the capstone.** *Needs Azure (calls are bounded).*
**Agent type:** the failure modes that page you at 2am — and the engineering control that stops each.

## The one idea
> Safety is a property of **your code**, not the model's goodwill. Budgets, turn caps, cycle
> detection, trust boundaries, and allowlists are engineering — not prompting.

## What it shows live (each guard engages on screen)
| Failure (triggered for real) | Guard |
|---|---|
| **Cost blowup** — a self-expanding crawl (1→2→4→8 fan-out) | a cumulative **token budget** → `BUDGET TRIPPED` |
| **Infinite loop** — an impossible goal (dial 68→71→68…) | **max-turn cap** + **cycle detector** → `CYCLE DETECTED` |
| **Prompt injection** — a malicious instruction hidden in fetched page content | tool output is **untrusted DATA**; destructive `delete_database` sits behind an **out-of-band allowlist** → refused, DB intact |

## Run
```bash
python demos/10_failure_modes/failure_modes.py
DEMO_FAILURE_MODE=injection python ...                 # just the injection case
DEMO_FAILURE_MODE=injection DEMO_ALLOW_DELETE=true python ...   # see what the allowlist was preventing
```

## Talking points
- Defense in depth: even if the model is *induced* to request a destructive action, the
  orchestration refuses it — the allowlist is the last line of defense.
- A budget and a cycle detector turn "unbounded and scary" into "capped and observable."
- This is the difference between a demo that works once and a system you'd run in production.
